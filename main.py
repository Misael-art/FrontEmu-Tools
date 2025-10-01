#!/usr/bin/env python3
"""
FrontEmu-Tools - Aplicação Principal

Aplicação principal do FrontEmu-Tools que inicializa a interface gráfica
seguindo a Clean Architecture e os requisitos do DRS.

Autor: FrontEmu-Tools Team
Versão: 1.0.0
"""

import logging
import sys
import traceback
from pathlib import Path

# Adicionar o diretório src ao path para importações
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon, QPixmap
except ImportError as e:
    print(f"❌ Erro ao importar PySide6: {e}")
    print("💡 Instale o PySide6 com: pip install PySide6")
    sys.exit(1)

from sd_emulation_gui.infrastructure.dependency_container import configure_container
from sd_emulation_gui.gui.main_window import MainWindow


def setup_logging() -> None:
    """Configura o sistema de logging da aplicação."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("frontemutools.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_application() -> QApplication:
    """Cria e configura a aplicação Qt.
    
    Returns:
        QApplication: Instância da aplicação Qt configurada
    """
    app = QApplication(sys.argv)
    
    # Configurações da aplicação
    app.setApplicationName("FrontEmu-Tools")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FrontEmu-Tools Team")
    app.setOrganizationDomain("frontemutools.com")
    
    # Configurar estilo da aplicação
    app.setStyle("Fusion")
    
    # Aplicar tema escuro moderno
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }
        
        QPushButton {
            background-color: #32CD32;
            color: #000000;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #28a428;
        }
        
        QPushButton:pressed {
            background-color: #228b22;
        }
        
        QPushButton:disabled {
            background-color: #666666;
            color: #999999;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #32CD32;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #32CD32;
        }
        
        QProgressBar {
            border: 2px solid #666666;
            border-radius: 5px;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #32CD32;
            border-radius: 3px;
        }
        
        QTabWidget::pane {
            border: 1px solid #666666;
            background-color: #2b2b2b;
        }
        
        QTabBar::tab {
            background-color: #404040;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #32CD32;
            color: #000000;
            font-weight: bold;
        }
        
        QTabBar::tab:hover {
            background-color: #555555;
        }
        
        QListWidget, QTreeWidget {
            background-color: #404040;
            border: 1px solid #666666;
            alternate-background-color: #4a4a4a;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #32CD32;
            color: #000000;
        }
        
        QScrollBar:vertical {
            background-color: #404040;
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
    
    return app


def show_error_dialog(title: str, message: str, details: str = None) -> None:
    """Exibe um diálogo de erro para o usuário.
    
    Args:
        title: Título do diálogo
        message: Mensagem principal
        details: Detalhes técnicos do erro (opcional)
    """
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if details:
        msg_box.setDetailedText(details)
    
    msg_box.exec_()


def main() -> int:
    """Função principal da aplicação.
    
    Returns:
        int: Código de saída da aplicação
    """
    try:
        # Configurar logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("🚀 Iniciando FrontEmu-Tools v1.0.0...")
        
        # Criar aplicação Qt
        app = create_application()
        
        # Configurar container de dependências
        logger.info("⚙️ Configurando container de dependências...")
        container = configure_container({})
        
        # Verificar se os serviços essenciais estão disponíveis
        essential_services = [
            ("SystemInfoService", container.get_system_info_service),
            ("DriveDetectionService", container.get_drive_detection_service),
            ("ConfigurationService", container.get_configuration_service),
            ("SystemStatsService", container.get_system_stats_service)
        ]
        
        for service_name, service_getter in essential_services:
            service = service_getter()
            if service is None:
                raise RuntimeError(f"Serviço essencial {service_name} não está disponível")
            logger.info(f"✅ {service_name} carregado com sucesso")
        
        # Criar e exibir janela principal
        logger.info("🖥️ Criando interface gráfica...")
        main_window = MainWindow(container)
        
        # Configurar janela
        main_window.setWindowTitle("FrontEmu-Tools v1.0.0")
        main_window.setMinimumSize(1200, 800)
        main_window.resize(1400, 900)
        
        # Centralizar janela na tela
        screen = app.primaryScreen().geometry()
        window_geometry = main_window.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        main_window.move(x, y)
        
        # Exibir janela
        main_window.show()
        
        logger.info("✅ FrontEmu-Tools iniciado com sucesso!")
        logger.info("📋 Interface gráfica carregada e pronta para uso")
        
        # Executar aplicação
        return app.exec_()
        
    except ImportError as e:
        error_msg = f"Erro de importação: {e}"
        logger.error(error_msg)
        
        if "PyQt5" in str(e):
            print("❌ PyQt5 não está instalado!")
            print("💡 Execute: pip install PyQt5")
        else:
            print(f"❌ {error_msg}")
            
        return 1
        
    except Exception as e:
        error_msg = f"Erro inesperado: {e}"
        error_details = traceback.format_exc()
        
        logger.error(error_msg)
        logger.error(error_details)
        
        # Tentar exibir diálogo de erro se possível
        try:
            show_error_dialog(
                "Erro Fatal",
                "Ocorreu um erro inesperado ao iniciar o FrontEmu-Tools.",
                error_details
            )
        except:
            print(f"❌ {error_msg}")
            print(f"📋 Detalhes: {error_details}")
            
        return 1


if __name__ == "__main__":
    """Ponto de entrada da aplicação."""
    exit_code = main()
    sys.exit(exit_code)