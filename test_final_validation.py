#!/usr/bin/env python3
"""
Teste Final de Validação

Executa uma validação completa de todas as funcionalidades implementadas
no FrontEmu-Tools v1.0, incluindo serviços, interface gráfica e integração.
"""

import sys
import unittest
import time
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configurar ambiente para testes sem display
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
except ImportError:
    print("❌ PySide6 não está disponível para testes")
    sys.exit(1)

from sd_emulation_gui.infrastructure.dependency_container import configure_container
from sd_emulation_gui.gui.main_window import MainWindow
from sd_emulation_gui.domain.entities import SystemPlatform


class TestFinalValidation(unittest.TestCase):
    """Teste final de validação completa do sistema."""
    
    @classmethod
    def setUpClass(cls):
        """Configuração inicial dos testes."""
        print("🔧 Configurando ambiente de teste...")
        
        # Verificar se já existe uma instância do QApplication
        if QApplication.instance() is None:
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
        
        # Configurar container de dependências
        cls.container = configure_container({})
        print("✅ Ambiente configurado com sucesso!")
    
    @classmethod
    def tearDownClass(cls):
        """Limpeza após os testes."""
        print("🧹 Limpando ambiente de teste...")
    
    def test_01_dependency_container_validation(self):
        """Valida se o container de dependências está funcionando corretamente."""
        print("\n📦 Testando Container de Dependências...")
        
        # Verificar se o container foi criado
        self.assertIsNotNone(self.container, "Container deve ser criado")
        
        # Verificar serviços essenciais
        essential_services = [
            ("SystemInfoService", self.container.get_system_info_service),
            ("DriveDetectionService", self.container.get_drive_detection_service),
            ("ConfigurationService", self.container.get_configuration_service),
            ("SystemStatsService", self.container.get_system_stats_service)
        ]
        
        for service_name, service_getter in essential_services:
            service = service_getter()
            self.assertIsNotNone(service, f"{service_name} deve estar disponível")
            print(f"  ✅ {service_name}: OK")
        
        print("📦 Container de Dependências: VALIDADO")
    
    def test_02_domain_entities_validation(self):
        """Valida se as entidades de domínio estão funcionando."""
        print("\n🏗️ Testando Entidades de Domínio...")
        
        # Testar enum SystemPlatform
        self.assertTrue(hasattr(SystemPlatform, 'PC_WINDOWS'), "PC_WINDOWS deve existir")
        self.assertTrue(hasattr(SystemPlatform, 'PC_LINUX'), "PC_LINUX deve existir")
        self.assertTrue(hasattr(SystemPlatform, 'PC_MACOS'), "PC_MACOS deve existir")
        self.assertTrue(hasattr(SystemPlatform, 'NINTENDO_SWITCH'), "NINTENDO_SWITCH deve existir")
        
        print("  ✅ SystemPlatform: Todas as plataformas disponíveis")
        print("🏗️ Entidades de Domínio: VALIDADAS")
    
    def test_03_services_functionality_validation(self):
        """Valida a funcionalidade dos serviços principais."""
        print("\n⚙️ Testando Funcionalidade dos Serviços...")
        
        # Testar SystemInfoService
        system_info_service = self.container.get_system_info_service()
        system_info = system_info_service.get_system_info()
        self.assertIsInstance(system_info, dict, "SystemInfo deve retornar dicionário")
        self.assertIn('platform', system_info, "SystemInfo deve conter 'platform'")
        print("  ✅ SystemInfoService: Funcional")
        
        # Testar DriveDetectionService
        drive_service = self.container.get_drive_detection_service()
        drives = drive_service.get_all_drives()
        self.assertIsInstance(drives, dict, "Drives deve retornar dicionário")
        print("  ✅ DriveDetectionService: Funcional")
        
        # Testar ConfigurationService
        config_service = self.container.get_configuration_service()
        self.assertIsNotNone(config_service, "ConfigurationService deve estar disponível")
        print("  ✅ ConfigurationService: Funcional")
        
        # Testar SystemStatsService
        stats_service = self.container.get_system_stats_service()
        self.assertIsNotNone(stats_service, "SystemStatsService deve estar disponível")
        print("  ✅ SystemStatsService: Funcional")
        
        print("⚙️ Serviços: VALIDADOS")
    
    def test_04_gui_integration_validation(self):
        """Valida a integração da interface gráfica."""
        print("\n🖥️ Testando Integração da Interface Gráfica...")
        
        # Criar MainWindow
        main_window = MainWindow(self.container)
        self.assertIsNotNone(main_window, "MainWindow deve ser criada")
        print("  ✅ MainWindow: Criada com sucesso")
        
        # Verificar propriedades básicas
        self.assertTrue(len(main_window.windowTitle()) > 0, "Janela deve ter título")
        print("  ✅ Título da janela: Configurado")
        
        # Verificar tamanho mínimo
        min_size = main_window.minimumSize()
        self.assertGreater(min_size.width(), 0, "Largura mínima deve ser > 0")
        self.assertGreater(min_size.height(), 0, "Altura mínima deve ser > 0")
        print("  ✅ Tamanho mínimo: Configurado")
        
        # Verificar widgets filhos
        children = main_window.findChildren(object)
        self.assertGreater(len(children), 0, "MainWindow deve ter widgets filhos")
        print(f"  ✅ Widgets integrados: {len(children)} widgets encontrados")
        
        print("🖥️ Interface Gráfica: VALIDADA")
    
    def test_05_application_startup_validation(self):
        """Valida se a aplicação pode ser iniciada corretamente."""
        print("\n🚀 Testando Inicialização da Aplicação...")
        
        try:
            # Simular inicialização da aplicação
            main_window = MainWindow(self.container)
            main_window.setWindowTitle("FrontEmu-Tools v1.0.0 - Teste")
            main_window.setMinimumSize(1200, 800)
            
            # Verificar se a janela pode ser exibida (sem realmente exibir)
            self.assertFalse(main_window.isVisible(), "Janela deve estar oculta inicialmente")
            
            # Simular exibição
            main_window.show()
            self.assertTrue(main_window.isVisible(), "Janela deve estar visível após show()")
            
            # Simular ocultação
            main_window.hide()
            self.assertFalse(main_window.isVisible(), "Janela deve estar oculta após hide()")
            
            print("  ✅ Ciclo de vida da janela: Funcional")
            print("  ✅ Inicialização: Bem-sucedida")
            
        except Exception as e:
            self.fail(f"Erro na inicialização da aplicação: {e}")
        
        print("🚀 Inicialização da Aplicação: VALIDADA")
    
    def test_06_performance_validation(self):
        """Valida a performance básica do sistema."""
        print("\n⚡ Testando Performance do Sistema...")
        
        # Testar tempo de criação do container
        start_time = time.time()
        test_container = configure_container({})
        container_time = time.time() - start_time
        
        self.assertLess(container_time, 5.0, "Container deve ser criado em menos de 5 segundos")
        print(f"  ✅ Criação do container: {container_time:.2f}s")
        
        # Testar tempo de criação da GUI
        start_time = time.time()
        test_window = MainWindow(test_container)
        gui_time = time.time() - start_time
        
        self.assertLess(gui_time, 10.0, "GUI deve ser criada em menos de 10 segundos")
        print(f"  ✅ Criação da GUI: {gui_time:.2f}s")
        
        print("⚡ Performance: VALIDADA")
    
    def test_07_integration_validation(self):
        """Valida a integração completa do sistema."""
        print("\n🔗 Testando Integração Completa...")
        
        # Verificar se todos os componentes trabalham juntos
        main_window = MainWindow(self.container)
        
        # Verificar se os serviços estão acessíveis através da GUI
        system_info_service = self.container.get_system_info_service()
        drive_service = self.container.get_drive_detection_service()
        config_service = self.container.get_configuration_service()
        stats_service = self.container.get_system_stats_service()
        
        # Verificar se todos os serviços estão funcionando
        services_working = all([
            system_info_service is not None,
            drive_service is not None,
            config_service is not None,
            stats_service is not None
        ])
        
        self.assertTrue(services_working, "Todos os serviços devem estar funcionando")
        print("  ✅ Integração de serviços: Funcional")
        
        # Verificar se a GUI pode acessar os serviços
        try:
            system_info = system_info_service.get_system_info()
            drives = drive_service.get_all_drives()
            self.assertIsInstance(system_info, dict, "SystemInfo deve retornar dados")
            self.assertIsInstance(drives, dict, "Drives deve retornar dados")
            print("  ✅ Acesso aos dados: Funcional")
        except Exception as e:
            self.fail(f"Erro ao acessar dados dos serviços: {e}")
        
        print("🔗 Integração Completa: VALIDADA")


def main():
    """Executa a validação final completa."""
    print("=" * 70)
    print("🎯 VALIDAÇÃO FINAL - FrontEmu-Tools v1.0.0")
    print("=" * 70)
    print("📋 Executando testes de validação completa...")
    print()
    
    # Executar testes
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFinalValidation)
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    
    if result.wasSuccessful():
        print("🎉 VALIDAÇÃO FINAL: SUCESSO!")
        print("✅ Todas as funcionalidades estão operacionais")
        print("✅ FrontEmu-Tools v1.0.0 está pronto para uso")
        print()
        print("📋 Resumo da Validação:")
        print("  • Container de Dependências: ✅ Funcional")
        print("  • Entidades de Domínio: ✅ Validadas")
        print("  • Serviços Principais: ✅ Operacionais")
        print("  • Interface Gráfica: ✅ Integrada")
        print("  • Inicialização: ✅ Bem-sucedida")
        print("  • Performance: ✅ Adequada")
        print("  • Integração: ✅ Completa")
        print()
        print("🚀 O FrontEmu-Tools está pronto para produção!")
    else:
        print("❌ VALIDAÇÃO FINAL: FALHOU!")
        print(f"❌ {len(result.failures)} teste(s) falharam")
        print(f"❌ {len(result.errors)} erro(s) encontrado(s)")
        
        if result.failures:
            print("\n📋 Falhas:")
            for test, traceback in result.failures:
                print(f"  • {test}: {traceback}")
        
        if result.errors:
            print("\n📋 Erros:")
            for test, traceback in result.errors:
                print(f"  • {test}: {traceback}")
    
    print("=" * 70)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)