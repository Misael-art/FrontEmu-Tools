"""
Infrastructure Layer

Camada de infraestrutura que implementa as interfaces definidas
na camada de domínio e fornece acesso a recursos externos.
"""

# Repositórios
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

# Adaptadores para serviços externos
from .adapters import (
    FileSystemServiceImpl,
    SystemMonitoringServiceImpl
)

# Container de dependências
from .dependency_container import (
    DependencyContainer,
    get_container,
    reset_container,
    configure_container
)

__all__ = [
    # Repositórios
    'DatabaseManager',
    'DriveRepositoryImpl',
    'EmulatorRepositoryImpl',
    'LegacyInstallationRepositoryImpl',
    'MigrationTaskRepositoryImpl',
    'ConfigurationRepositoryImpl',
    'SystemAlertRepositoryImpl',
    'SystemSessionRepositoryImpl',
    
    # Adaptadores
    'FileSystemServiceImpl',
    'SystemMonitoringServiceImpl',
    
    # Container de dependências
    'DependencyContainer',
    'get_container',
    'reset_container',
    'configure_container'
]