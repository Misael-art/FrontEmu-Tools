#!/usr/bin/env python3
"""
Teste de Integração da Interface Gráfica

Testa se a interface gráfica do FrontEmu-Tools pode ser inicializada
corretamente com todos os widgets e serviços funcionando.
"""

import sys
import unittest
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configurar ambiente para testes sem display
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
except ImportError:
    print("❌ PySide6 não está disponível para testes")
    sys.exit(1)

from sd_emulation_gui.infrastructure.dependency_container import configure_container
from sd_emulation_gui.gui.main_window import MainWindow


class TestGUIIntegration(unittest.TestCase):
    """Testes de integração da interface gráfica."""
    
    @classmethod
    def setUpClass(cls):
        """Configuração inicial dos testes."""
        # Verificar se já existe uma instância do QApplication
        if QApplication.instance() is None:
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
        cls.container = configure_container({})
    
    @classmethod
    def tearDownClass(cls):
        """Limpeza após os testes."""
        cls.app.quit()
    
    def test_main_window_creation(self):
        """Testa se a janela principal pode ser criada."""
        try:
            main_window = MainWindow(self.container)
            self.assertIsNotNone(main_window, "MainWindow deve ser criada")
            print("✅ MainWindow criada com sucesso")
        except Exception as e:
            self.fail(f"Erro ao criar MainWindow: {e}")
    
    def test_main_window_initialization(self):
        """Testa se a janela principal é inicializada corretamente."""
        try:
            main_window = MainWindow(self.container)
            
            # Verificar se a janela tem título
            self.assertTrue(len(main_window.windowTitle()) > 0, "Janela deve ter título")
            
            # Verificar se a janela tem tamanho mínimo
            min_size = main_window.minimumSize()
            self.assertGreater(min_size.width(), 0, "Largura mínima deve ser > 0")
            self.assertGreater(min_size.height(), 0, "Altura mínima deve ser > 0")
            
            print("✅ MainWindow inicializada corretamente")
        except Exception as e:
            self.fail(f"Erro na inicialização da MainWindow: {e}")
    
    def test_widgets_integration(self):
        """Testa se os widgets estão integrados corretamente."""
        try:
            main_window = MainWindow(self.container)
            
            # Verificar se a janela tem widgets filhos
            children = main_window.findChildren(object)
            self.assertGreater(len(children), 0, "MainWindow deve ter widgets filhos")
            
            print(f"✅ MainWindow tem {len(children)} widgets integrados")
        except Exception as e:
            self.fail(f"Erro na integração de widgets: {e}")
    
    def test_services_integration(self):
        """Testa se os serviços estão integrados corretamente na GUI."""
        try:
            main_window = MainWindow(self.container)
            
            # Verificar se os serviços essenciais estão disponíveis
            essential_services = [
                ("SystemInfoService", self.container.get_system_info_service),
                ("DriveDetectionService", self.container.get_drive_detection_service),
                ("ConfigurationService", self.container.get_configuration_service),
                ("SystemStatsService", self.container.get_system_stats_service)
            ]
            
            for service_name, service_getter in essential_services:
                service = service_getter()
                self.assertIsNotNone(service, f"{service_name} deve estar disponível")
            
            print("✅ Todos os serviços essenciais estão integrados")
        except Exception as e:
            self.fail(f"Erro na integração de serviços: {e}")
    
    def test_window_show_hide(self):
        """Testa se a janela pode ser exibida e ocultada."""
        try:
            main_window = MainWindow(self.container)
            
            # Testar exibição
            main_window.show()
            self.assertTrue(main_window.isVisible(), "Janela deve estar visível após show()")
            
            # Testar ocultação
            main_window.hide()
            self.assertFalse(main_window.isVisible(), "Janela deve estar oculta após hide()")
            
            print("✅ Exibição e ocultação da janela funcionando")
        except Exception as e:
            self.fail(f"Erro ao exibir/ocultar janela: {e}")
    
    def test_window_resize(self):
        """Testa se a janela pode ser redimensionada."""
        try:
            main_window = MainWindow(self.container)
            
            # Testar redimensionamento
            main_window.resize(800, 600)
            size = main_window.size()
            self.assertEqual(size.width(), 800, "Largura deve ser 800")
            self.assertEqual(size.height(), 600, "Altura deve ser 600")
            
            print("✅ Redimensionamento da janela funcionando")
        except Exception as e:
            self.fail(f"Erro ao redimensionar janela: {e}")


def main():
    """Executa os testes de integração da GUI."""
    print("🧪 Iniciando testes de integração da interface gráfica...")
    print("=" * 60)
    
    # Executar testes
    unittest.main(verbosity=2, exit=False)
    
    print("=" * 60)
    print("✅ Testes de integração da GUI concluídos!")


if __name__ == "__main__":
    main()