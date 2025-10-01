#!/usr/bin/env python3
"""
Base Path Selector Widget

Este widget permite ao usuário selecionar o diretório base onde a estrutura 
de emulação será criada, com detecção automática de drives disponíveis.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QFileDialog, QGroupBox, QMessageBox,
    QTextBrowser, QFrame
)

# Add src path for imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

try:
    from utils.file_utils import FileUtils
    from utils.path_utils import PathUtils
except ImportError:
    # Fallback implementations
    class FileUtils:
        @staticmethod
        def write_json_file(path: str, data: dict) -> bool:
            import json
            import os
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
            except Exception:
                return False
        
        @staticmethod
        def read_json_file(path: str) -> dict:
            import json
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
    
    class PathUtils:
        @staticmethod
        def normalize_path(path) -> str:
            return os.path.normpath(str(path))
        
        @staticmethod
        def path_exists(path: str) -> bool:
            return os.path.exists(path)


class BasePathSelector(QWidget):
    """Widget para seleção do diretório base da estrutura de emulação."""
    
    # Signal emitido quando o path base é alterado
    base_path_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_settings()
        self.populate_drives()
        
    def setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        
        # Group box principal
        group = QGroupBox("Configuração do Diretório Base")
        group_layout = QVBoxLayout(group)
        
        # Descrição
        description = QLabel(
            "Selecione onde a estrutura de emulação será criada. "
            "Por padrão, será usado o diretório raiz do drive atual."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; font-size: 12px;")
        group_layout.addWidget(description)
        
        # Frame com opções
        options_frame = QFrame()
        options_layout = QVBoxLayout(options_frame)
        
        # Opção 1: Drives disponíveis
        drives_layout = QHBoxLayout()
        drives_layout.addWidget(QLabel("Drive/Raiz:"))
        
        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumWidth(200)
        self.drive_combo.currentTextChanged.connect(self._on_drive_changed)
        drives_layout.addWidget(self.drive_combo)
        
        drives_layout.addStretch()
        options_layout.addLayout(drives_layout)
        
        # Opção 2: Caminho personalizado
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Ou selecionar pasta:"))
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Selecione um diretório personalizado...")
        self.path_edit.textChanged.connect(self._on_path_changed)
        custom_layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton("Procurar...")
        self.browse_button.clicked.connect(self._browse_directory)
        custom_layout.addWidget(self.browse_button)
        
        options_layout.addLayout(custom_layout)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        options_layout.addWidget(line)
        
        # Path atual selecionado
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Diretório selecionado:"))
        
        self.current_path_label = QLabel()
        self.current_path_label.setStyleSheet(
            "font-weight: bold; color: #2b5aa0; font-family: 'Consolas', 'Monaco', monospace;"
        )
        self.current_path_label.setWordWrap(True)
        current_layout.addWidget(self.current_path_label, 1)
        
        options_layout.addLayout(current_layout)
        
        # Preview da estrutura que será criada
        preview_label = QLabel("Estrutura que será criada:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        options_layout.addWidget(preview_label)
        
        self.structure_preview = QTextBrowser()
        self.structure_preview.setMaximumHeight(120)
        self.structure_preview.setStyleSheet("""
            QTextBrowser {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        options_layout.addWidget(self.structure_preview)
        
        group_layout.addWidget(options_frame)
        
        # Botões de ação
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.apply_button = QPushButton("Aplicar Configuração")
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #2b5aa0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e3f73;
            }
        """)
        self.apply_button.clicked.connect(self._apply_settings)
        buttons_layout.addWidget(self.apply_button)
        
        self.reset_button = QPushButton("Usar Padrão")
        self.reset_button.clicked.connect(self._reset_to_default)
        buttons_layout.addWidget(self.reset_button)
        
        group_layout.addLayout(buttons_layout)
        
        layout.addWidget(group)
        
        # Inicializar com drive atual
        self._set_default_path()
        
    def populate_drives(self):
        """Popula a combo box com drives disponíveis."""
        self.drive_combo.clear()
        
        if sys.platform == "win32":
            # Windows - listar drives disponíveis
            import string
            available_drives = []
            
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    # Tentar determinar o tipo e nome do drive
                    try:
                        free_space = self._get_free_space(drive)
                        if free_space > 0:  # Drive acessível
                            drive_info = f"{letter}:\\ ({self._format_size(free_space)} livres)"
                            available_drives.append((drive, drive_info))
                    except:
                        # Drive não acessível, adicionar sem informações extras
                        available_drives.append((drive, f"{letter}:\\"))
            
            for drive_path, drive_info in available_drives:
                self.drive_combo.addItem(drive_info, drive_path)
                
        else:
            # Unix/Linux - mostrar diretórios comuns
            common_paths = [
                ("/", "/ (Raiz do Sistema)"),
                (os.path.expanduser("~"), "~ (Diretório Home)"),
                ("/opt", "/opt (Aplicações Opcionais)"),
                ("/usr/local", "/usr/local (Programas Locais)")
            ]
            
            for path, description in common_paths:
                if os.path.exists(path):
                    self.drive_combo.addItem(description, path)
        
        # Definir o drive atual como selecionado
        current_drive = Path.cwd().anchor
        if current_drive:
            for i in range(self.drive_combo.count()):
                if self.drive_combo.itemData(i) == current_drive:
                    self.drive_combo.setCurrentIndex(i)
                    break
    
    def _get_free_space(self, path: str) -> int:
        """Obtém o espaço livre em bytes para o caminho especificado."""
        try:
            if sys.platform == "win32":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path), 
                    ctypes.pointer(free_bytes), 
                    None, 
                    None
                )
                return free_bytes.value
            else:
                statvfs = os.statvfs(path)
                return statvfs.f_frsize * statvfs.f_avail
        except:
            return 0
    
    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _set_default_path(self):
        """Define o caminho padrão (raiz do drive atual)."""
        current_drive = Path.cwd().anchor
        if current_drive:
            self.current_path_label.setText(current_drive)
            self._update_structure_preview(current_drive)
    
    def _on_drive_changed(self, text: str):
        """Chamado quando um drive é selecionado na combo box."""
        if text:
            drive_path = self.drive_combo.currentData()
            if drive_path:
                self.path_edit.clear()  # Limpar campo personalizado
                self.current_path_label.setText(drive_path)
                self._update_structure_preview(drive_path)
    
    def _on_path_changed(self, text: str):
        """Chamado quando o caminho personalizado é alterado."""
        if text:
            # Limpar seleção de drive quando usando caminho personalizado
            self.drive_combo.setCurrentIndex(-1)
            self.current_path_label.setText(text)
            self._update_structure_preview(text)
    
    def _browse_directory(self):
        """Abre diálogo para seleção de diretório."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Selecionar Diretório Base",
            self.get_current_path()
        )
        
        if directory:
            self.path_edit.setText(directory)
    
    def _update_structure_preview(self, base_path: str):
        """Atualiza o preview da estrutura que será criada."""
        if not base_path:
            self.structure_preview.clear()
            return
        
        try:
            base = Path(base_path)
            structure = f"""
📁 {base}
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
            """.strip()
            
            self.structure_preview.setPlainText(structure)
        except Exception:
            self.structure_preview.setPlainText("Estrutura será criada no diretório selecionado")
    
    def _apply_settings(self):
        """Aplica as configurações selecionadas."""
        current_path = self.get_current_path()
        
        if not current_path:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um diretório válido.")
            return
        
        # Verificar se o diretório é acessível
        try:
            if not os.path.exists(current_path):
                reply = QMessageBox.question(
                    self, 
                    "Diretório não existe",
                    f"O diretório '{current_path}' não existe.\n\nDeseja criá-lo?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    os.makedirs(current_path, exist_ok=True)
                else:
                    return
            
            # Testar permissões de escrita
            test_file = Path(current_path) / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                QMessageBox.warning(
                    self, 
                    "Erro de Permissão",
                    f"Não é possível escrever no diretório '{current_path}'.\n\n"
                    "Verifique as permissões ou execute como administrador."
                )
                return
            
            # Salvar configuração
            self.save_settings()
            
            # Emitir signal com o novo path
            self.base_path_changed.emit(current_path)
            
            QMessageBox.information(
                self, 
                "Configuração Aplicada",
                f"Diretório base configurado para:\n{current_path}\n\n"
                "A estrutura de emulação será criada neste local."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao configurar diretório base:\n{str(e)}"
            )
    
    def _reset_to_default(self):
        """Reseta para o diretório padrão (raiz do drive atual)."""
        current_drive = Path.cwd().anchor
        if current_drive:
            # Selecionar drive na combo box
            for i in range(self.drive_combo.count()):
                if self.drive_combo.itemData(i) == current_drive:
                    self.drive_combo.setCurrentIndex(i)
                    break
            
            # Limpar campo personalizado
            self.path_edit.clear()
    
    def get_current_path(self) -> str:
        """Retorna o caminho atualmente selecionado."""
        # Priorizar campo personalizado se preenchido
        custom_path = self.path_edit.text().strip()
        if custom_path:
            return custom_path
        
        # Caso contrário, usar drive selecionado
        return self.drive_combo.currentData() or ""
    
    def set_current_path(self, path: str):
        """Define o caminho atual."""
        if not path:
            return
        
        path = os.path.normpath(path)
        
        # Verificar se é um dos drives disponíveis
        for i in range(self.drive_combo.count()):
            if self.drive_combo.itemData(i) == path:
                self.drive_combo.setCurrentIndex(i)
                self.path_edit.clear()
                return
        
        # Caso contrário, definir como caminho personalizado
        self.path_edit.setText(path)
        self.drive_combo.setCurrentIndex(-1)
    
    def save_settings(self):
        """Salva as configurações atuais."""
        current_path = self.get_current_path()
        if not current_path:
            return
        
        try:
            config_dir = Path.home() / ".sd_emulation_gui"
            config_dir.mkdir(exist_ok=True)
            
            settings = {
                "base_path": current_path,
                "last_updated": str(Path.cwd())
            }
            
            FileUtils.write_json_file(str(config_dir / "base_path.json"), settings)
        except Exception as e:
            print(f"Warning: Could not save base path settings: {e}")
    
    def load_settings(self):
        """Carrega as configurações salvas."""
        try:
            config_file = Path.home() / ".sd_emulation_gui" / "base_path.json"
            if config_file.exists():
                settings = FileUtils.read_json_file(str(config_file))
                saved_path = settings.get("base_path")
                
                if saved_path and os.path.exists(saved_path):
                    self.set_current_path(saved_path)
                    return
        except Exception as e:
            print(f"Warning: Could not load base path settings: {e}")
        
        # Se não conseguiu carregar configurações, usar padrão
        self._set_default_path()


if __name__ == "__main__":
    # Teste do widget
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = BasePathSelector()
    widget.setWindowTitle("Seletor de Diretório Base")
    widget.resize(600, 500)
    widget.show()
    
    def on_path_changed(path):
        print(f"Novo diretório base: {path}")
    
    widget.base_path_changed.connect(on_path_changed)
    
    sys.exit(app.exec())