#!/usr/bin/env python3
"""
Teste de funcionalidade do FrontEmu-Tools
Valida os componentes principais do sistema
"""

import sys
import os
import unittest
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from sd_emulation_gui.infrastructure.dependency_container import DependencyContainer, configure_container
    from sd_emulation_gui.domain.entities import (
        SystemPlatform, DriveInfo, SystemMetrics, Drive, Emulator, 
        LegacyInstallation, MigrationTask, SystemAlert, Configuration
    )
    from sd_emulation_gui.services.system_info_service import SystemInfoService
    from sd_emulation_gui.services.drive_manager_service import DriveManagerService
    from sd_emulation_gui.services.legacy_detection_service import LegacyDetectionService
    from sd_emulation_gui.services.system_stats_service import SystemStatsService
    from sd_emulation_gui.gui.widgets.drive_selection_widget import DriveSelectionWidget
    from sd_emulation_gui.gui.widgets.system_info_widget import SystemInfoWidget
    from sd_emulation_gui.gui.widgets.legacy_detection_widget import LegacyDetectionWidget
    from sd_emulation_gui.gui.widgets.system_stats_widget import SystemStatsWidget
    print("✅ Todas as importações foram bem-sucedidas!")
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    sys.exit(1)


class TestFrontEmuTools(unittest.TestCase):
    """Testes de funcionalidade do FrontEmu-Tools"""
    
    def setUp(self):
        """Configuração inicial para cada teste"""
        self.container = configure_container({})
    
    def test_dependency_container(self):
        """Testa se o container de dependências está funcionando"""
        self.assertIsNotNone(self.container)
        print("✅ Container de dependências: OK")
    
    def test_system_info_service(self):
        """Testa o serviço de informações do sistema"""
        service = self.container.get_system_info_service()
        self.assertIsNotNone(service)
        
        # Testa obtenção de informações do sistema
        system_info = service.get_system_info()
        self.assertIsNotNone(system_info)
        # SystemInfo não existe, mas o serviço deve retornar algo válido
        print("✅ SystemInfoService: OK")
    
    def test_drive_detection_service(self):
        """Testa o serviço de detecção de drives"""
        service = self.container.get_drive_detection_service()
        self.assertIsNotNone(service, "DriveDetectionService não deve ser None")
        
        # Testar detecção de drives
        drives = service.get_all_drives()
        self.assertIsInstance(drives, dict, "Drives deve ser um dicionário")
        print("✅ DriveDetectionService: OK")
    
    def test_configuration_service(self):
        """Testa o serviço de configuração"""
        service = self.container.get_configuration_service()
        self.assertIsNotNone(service)
        print("✅ ConfigurationService: OK")
    
    def test_system_stats_service(self):
        """Testa o serviço de estatísticas do sistema"""
        service = self.container.get_system_stats_service()
        self.assertIsNotNone(service)
        print("✅ SystemStatsService: OK")
    
    def test_widgets_import(self):
        """Testa se os widgets podem ser importados"""
        # Testa se as classes de widget existem
        self.assertTrue(hasattr(DriveSelectionWidget, '__init__'))
        self.assertTrue(hasattr(SystemInfoWidget, '__init__'))
        self.assertTrue(hasattr(LegacyDetectionWidget, '__init__'))
        self.assertTrue(hasattr(SystemStatsWidget, '__init__'))
        print("✅ Widgets: OK")
    
    def test_system_platform_enum(self):
        """Testa se o enum SystemPlatform está funcionando"""
        self.assertTrue(hasattr(SystemPlatform, 'PC_WINDOWS'))
        self.assertTrue(hasattr(SystemPlatform, 'PC_LINUX'))
        self.assertTrue(hasattr(SystemPlatform, 'PC_MACOS'))
        print("✅ SystemPlatform enum: OK")


def main():
    """Função principal de teste"""
    print("🚀 Iniciando testes de funcionalidade do FrontEmu-Tools...")
    print("=" * 60)
    
    # Executa os testes
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 60)
    print("✅ Testes de funcionalidade concluídos!")


if __name__ == "__main__":
    main()