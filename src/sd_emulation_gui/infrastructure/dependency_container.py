"""
Dependency Injection Container

Container de injeção de dependências que configura e fornece
todas as dependências da aplicação seguindo Clean Architecture.
"""

from typing import Dict, Any, Optional
import logging

from ..domain.use_cases import (
    # Use Cases
    DetectDrivesUseCase,
    SelectEmulationDriveUseCase,
    DetectEmulatorsUseCase,
    ConfigureEmulatorUseCase,
    DetectLegacyInstallationsUseCase,
    CreateMigrationTaskUseCase,
    ExecuteMigrationUseCase,
    MonitorSystemPerformanceUseCase,
    StartSystemSessionUseCase,
    EndSystemSessionUseCase,
    
    # Repository Interfaces
    DriveRepository,
    EmulatorRepository,
    LegacyInstallationRepository,
    MigrationTaskRepository,
    ConfigurationRepository,
    SystemAlertRepository,
    SystemSessionRepository,
    
    # Service Interfaces
    FileSystemService,
    SystemMonitoringService
)

from .repositories import (
    DatabaseManager,
    DriveRepositoryImpl,
    EmulatorRepositoryImpl,
    LegacyInstallationRepositoryImpl,
    MigrationTaskRepositoryImpl,
    ConfigurationRepositoryImpl,
    SystemAlertRepositoryImpl,
    SystemSessionRepositoryImpl
)

from .adapters import (
    FileSystemServiceImpl,
    SystemMonitoringServiceImpl
)

# Importar serviços existentes para compatibilidade
from ..services.system_info_service import SystemInfoService
from ..services.drive_detection_service import DriveDetectionService
from ..services.configuration_service import ConfigurationService
from ..services.system_stats_service import SystemStatsService


class DependencyContainer:
    """Container de injeção de dependências."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa o container de dependências."""
        self.config = config or {}
        self._instances: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)
        
        # Configurar banco de dados
        db_path = self.config.get('database_path')
        self._db_manager = DatabaseManager(db_path)
        
        self._setup_dependencies()
    
    def _setup_dependencies(self):
        """Configura todas as dependências."""
        try:
            # Serviços de infraestrutura
            self._register_infrastructure_services()
            
            # Repositórios
            self._register_repositories()
            
            # Casos de uso
            self._register_use_cases()
            
            # Serviços legados (para compatibilidade)
            self._register_legacy_services()
            
            self._logger.info("Container de dependências configurado com sucesso")
            
        except Exception as e:
            self._logger.error(f"Erro ao configurar dependências: {e}")
            raise
    
    def _register_infrastructure_services(self):
        """Registra serviços de infraestrutura."""
        # Serviços externos
        self._instances['file_system_service'] = FileSystemServiceImpl()
        self._instances['system_monitoring_service'] = SystemMonitoringServiceImpl()
        
        # Gerenciador de banco de dados
        self._instances['database_manager'] = self._db_manager
    
    def _register_repositories(self):
        """Registra repositórios."""
        db_manager = self._instances['database_manager']
        
        # Repositórios básicos
        self._instances['drive_repository'] = DriveRepositoryImpl(db_manager)
        self._instances['emulator_repository'] = EmulatorRepositoryImpl(db_manager)
        self._instances['legacy_installation_repository'] = LegacyInstallationRepositoryImpl(db_manager)
        self._instances['configuration_repository'] = ConfigurationRepositoryImpl(db_manager)
        self._instances['system_alert_repository'] = SystemAlertRepositoryImpl(db_manager)
        self._instances['system_session_repository'] = SystemSessionRepositoryImpl(db_manager)
        
        # Repositório de migração (precisa de outros repositórios)
        self._instances['migration_task_repository'] = MigrationTaskRepositoryImpl(
            db_manager,
            self._instances['legacy_installation_repository'],
            self._instances['drive_repository']
        )
    
    def _register_use_cases(self):
        """Registra casos de uso."""
        # Casos de uso para drives
        self._instances['detect_drives_use_case'] = DetectDrivesUseCase(
            self._instances['drive_repository'],
            self._instances['file_system_service']
        )
        
        self._instances['select_emulation_drive_use_case'] = SelectEmulationDriveUseCase(
            self._instances['drive_repository']
        )
        
        # Casos de uso para emuladores
        self._instances['detect_emulators_use_case'] = DetectEmulatorsUseCase(
            self._instances['emulator_repository'],
            self._instances['file_system_service']
        )
        
        self._instances['configure_emulator_use_case'] = ConfigureEmulatorUseCase(
            self._instances['emulator_repository'],
            self._instances['configuration_repository']
        )
        
        # Casos de uso para instalações legacy
        self._instances['detect_legacy_installations_use_case'] = DetectLegacyInstallationsUseCase(
            self._instances['legacy_installation_repository'],
            self._instances['file_system_service']
        )
        
        # Casos de uso para migração
        self._instances['create_migration_task_use_case'] = CreateMigrationTaskUseCase(
            self._instances['migration_task_repository'],
            self._instances['drive_repository']
        )
        
        self._instances['execute_migration_use_case'] = ExecuteMigrationUseCase(
            self._instances['migration_task_repository'],
            self._instances['file_system_service']
        )
        
        # Casos de uso para monitoramento
        self._instances['monitor_system_performance_use_case'] = MonitorSystemPerformanceUseCase(
            self._instances['system_alert_repository'],
            self._instances['system_monitoring_service']
        )
        
        # Casos de uso para sessão
        self._instances['start_system_session_use_case'] = StartSystemSessionUseCase(
            self._instances['system_session_repository']
        )
        
        self._instances['end_system_session_use_case'] = EndSystemSessionUseCase(
            self._instances['system_session_repository']
        )
    
    def _register_legacy_services(self):
        """Registra serviços legados para compatibilidade."""
        try:
            # SystemInfoService existente
            self._instances['system_info_service'] = SystemInfoService()
            
            # DriveDetectionService existente
            self._instances['drive_detection_service'] = DriveDetectionService()
            
            # ConfigurationService existente
            self._instances['configuration_service'] = ConfigurationService()
            
            # SystemStatsService existente
            self._instances['system_stats_service'] = SystemStatsService()
            
        except Exception as e:
            self._logger.warning(f"Erro ao registrar serviços legados: {e}")
            # Continuar sem os serviços legados se houver erro
    
    def get(self, service_name: str) -> Any:
        """Obtém uma instância de serviço."""
        if service_name not in self._instances:
            raise ValueError(f"Serviço '{service_name}' não encontrado no container")
        
        return self._instances[service_name]
    
    def get_drive_repository(self) -> DriveRepository:
        """Obtém repositório de drives."""
        return self.get('drive_repository')
    
    def get_emulator_repository(self) -> EmulatorRepository:
        """Obtém repositório de emuladores."""
        return self.get('emulator_repository')
    
    def get_legacy_installation_repository(self) -> LegacyInstallationRepository:
        """Obtém repositório de instalações legacy."""
        return self.get('legacy_installation_repository')
    
    def get_migration_task_repository(self) -> MigrationTaskRepository:
        """Obtém repositório de tarefas de migração."""
        return self.get('migration_task_repository')
    
    def get_configuration_repository(self) -> ConfigurationRepository:
        """Obtém repositório de configurações."""
        return self.get('configuration_repository')
    
    def get_system_alert_repository(self) -> SystemAlertRepository:
        """Obtém repositório de alertas."""
        return self.get('system_alert_repository')
    
    def get_system_session_repository(self) -> SystemSessionRepository:
        """Obtém repositório de sessões."""
        return self.get('system_session_repository')
    
    def get_file_system_service(self) -> FileSystemService:
        """Obtém serviço de sistema de arquivos."""
        return self.get('file_system_service')
    
    def get_system_monitoring_service(self) -> SystemMonitoringService:
        """Obtém serviço de monitoramento."""
        return self.get('system_monitoring_service')
    
    # Use Cases
    def get_detect_drives_use_case(self) -> DetectDrivesUseCase:
        """Obtém caso de uso para detectar drives."""
        return self.get('detect_drives_use_case')
    
    def get_select_emulation_drive_use_case(self) -> SelectEmulationDriveUseCase:
        """Obtém caso de uso para selecionar drive de emulação."""
        return self.get('select_emulation_drive_use_case')
    
    def get_detect_emulators_use_case(self) -> DetectEmulatorsUseCase:
        """Obtém caso de uso para detectar emuladores."""
        return self.get('detect_emulators_use_case')
    
    def get_configure_emulator_use_case(self) -> ConfigureEmulatorUseCase:
        """Obtém caso de uso para configurar emulador."""
        return self.get('configure_emulator_use_case')
    
    def get_detect_legacy_installations_use_case(self) -> DetectLegacyInstallationsUseCase:
        """Obtém caso de uso para detectar instalações legacy."""
        return self.get('detect_legacy_installations_use_case')
    
    def get_create_migration_task_use_case(self) -> CreateMigrationTaskUseCase:
        """Obtém caso de uso para criar tarefa de migração."""
        return self.get('create_migration_task_use_case')
    
    def get_execute_migration_use_case(self) -> ExecuteMigrationUseCase:
        """Obtém caso de uso para executar migração."""
        return self.get('execute_migration_use_case')
    
    def get_monitor_system_performance_use_case(self) -> MonitorSystemPerformanceUseCase:
        """Obtém caso de uso para monitorar performance."""
        return self.get('monitor_system_performance_use_case')
    
    def get_start_system_session_use_case(self) -> StartSystemSessionUseCase:
        """Obtém caso de uso para iniciar sessão."""
        return self.get('start_system_session_use_case')
    
    def get_end_system_session_use_case(self) -> EndSystemSessionUseCase:
        """Obtém caso de uso para finalizar sessão."""
        return self.get('end_system_session_use_case')
    
    # Serviços legados (para compatibilidade)
    def get_system_info_service(self) -> Optional[SystemInfoService]:
        """Obtém serviço de informações do sistema (legacy)."""
        return self._instances.get('system_info_service')
    
    def get_drive_detection_service(self) -> Optional[DriveDetectionService]:
        """Obtém serviço de detecção de drives (legacy)."""
        return self._instances.get('drive_detection_service')
    
    def get_configuration_service(self) -> Optional[ConfigurationService]:
        """Obtém serviço de configuração (legacy)."""
        return self._instances.get('configuration_service')
    
    def get_system_stats_service(self) -> Optional[SystemStatsService]:
        """Obtém serviço de estatísticas do sistema (legacy)."""
        return self._instances.get('system_stats_service')
    
    def register_instance(self, name: str, instance: Any):
        """Registra uma instância personalizada."""
        self._instances[name] = instance
        self._logger.debug(f"Instância '{name}' registrada no container")
    
    def has_service(self, service_name: str) -> bool:
        """Verifica se um serviço está registrado."""
        return service_name in self._instances
    
    def list_services(self) -> list[str]:
        """Lista todos os serviços registrados."""
        return list(self._instances.keys())
    
    def clear(self):
        """Limpa todas as instâncias do container."""
        self._instances.clear()
        self._logger.info("Container de dependências limpo")
    
    def shutdown(self):
        """Finaliza o container e limpa recursos."""
        try:
            # Finalizar serviços que precisam de cleanup
            if 'system_stats_service' in self._instances:
                stats_service = self._instances['system_stats_service']
                if hasattr(stats_service, 'stop_monitoring'):
                    stats_service.stop_monitoring()
            
            # Fechar conexões de banco de dados
            if hasattr(self._db_manager, 'close'):
                self._db_manager.close()
            
            self.clear()
            self._logger.info("Container de dependências finalizado")
            
        except Exception as e:
            self._logger.error(f"Erro ao finalizar container: {e}")


# Instância global do container (singleton)
_container_instance: Optional[DependencyContainer] = None


def get_container(config: Optional[Dict[str, Any]] = None) -> DependencyContainer:
    """Obtém a instância global do container de dependências."""
    global _container_instance
    
    if _container_instance is None:
        _container_instance = DependencyContainer(config)
    
    return _container_instance


def reset_container():
    """Reseta a instância global do container."""
    global _container_instance
    
    if _container_instance:
        _container_instance.shutdown()
    
    _container_instance = None


def configure_container(config: Dict[str, Any]) -> DependencyContainer:
    """Configura e obtém o container com configurações específicas."""
    reset_container()
    return get_container(config)