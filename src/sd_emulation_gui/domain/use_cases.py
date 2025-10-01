"""
Domain Use Cases

Casos de uso que implementam a lógica de negócio do sistema FrontEmu-Tools
seguindo os princípios da Clean Architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple
from uuid import UUID

from .entities import (
    AlertSeverity,
    Configuration,
    Drive,
    DriveInfo,
    DriveType,
    Emulator,
    EmulatorStatus,
    LegacyInstallation,
    MigrationStatus,
    MigrationTask,
    SystemAlert,
    SystemMetrics,
    SystemPlatform,
    SystemSession
)


# Interfaces de repositório (serão implementadas na camada de infraestrutura)
class DriveRepository(Protocol):
    """Interface para repositório de drives."""
    
    def get_all_drives(self) -> List[Drive]:
        """Obtém todos os drives."""
        ...
    
    def get_drive_by_letter(self, letter: str) -> Optional[Drive]:
        """Obtém drive por letra."""
        ...
    
    def save_drive(self, drive: Drive) -> None:
        """Salva drive."""
        ...
    
    def delete_drive(self, drive_id: UUID) -> None:
        """Remove drive."""
        ...


class EmulatorRepository(Protocol):
    """Interface para repositório de emuladores."""
    
    def get_all_emulators(self) -> List[Emulator]:
        """Obtém todos os emuladores."""
        ...
    
    def get_emulator_by_name(self, name: str) -> Optional[Emulator]:
        """Obtém emulador por nome."""
        ...
    
    def get_emulators_by_platform(self, platform: SystemPlatform) -> List[Emulator]:
        """Obtém emuladores por plataforma."""
        ...
    
    def save_emulator(self, emulator: Emulator) -> None:
        """Salva emulador."""
        ...
    
    def delete_emulator(self, emulator_id: UUID) -> None:
        """Remove emulador."""
        ...


class LegacyInstallationRepository(Protocol):
    """Interface para repositório de instalações legacy."""
    
    def get_all_installations(self) -> List[LegacyInstallation]:
        """Obtém todas as instalações."""
        ...
    
    def get_installation_by_path(self, path: str) -> Optional[LegacyInstallation]:
        """Obtém instalação por caminho."""
        ...
    
    def save_installation(self, installation: LegacyInstallation) -> None:
        """Salva instalação."""
        ...
    
    def delete_installation(self, installation_id: UUID) -> None:
        """Remove instalação."""
        ...


class MigrationTaskRepository(Protocol):
    """Interface para repositório de tarefas de migração."""
    
    def get_all_tasks(self) -> List[MigrationTask]:
        """Obtém todas as tarefas."""
        ...
    
    def get_task_by_id(self, task_id: UUID) -> Optional[MigrationTask]:
        """Obtém tarefa por ID."""
        ...
    
    def get_tasks_by_status(self, status: MigrationStatus) -> List[MigrationTask]:
        """Obtém tarefas por status."""
        ...
    
    def save_task(self, task: MigrationTask) -> None:
        """Salva tarefa."""
        ...
    
    def delete_task(self, task_id: UUID) -> None:
        """Remove tarefa."""
        ...


class ConfigurationRepository(Protocol):
    """Interface para repositório de configurações."""
    
    def get_all_configurations(self) -> List[Configuration]:
        """Obtém todas as configurações."""
        ...
    
    def get_configuration_by_name(self, name: str) -> Optional[Configuration]:
        """Obtém configuração por nome."""
        ...
    
    def get_configurations_by_emulator(self, emulator_name: str) -> List[Configuration]:
        """Obtém configurações por emulador."""
        ...
    
    def save_configuration(self, configuration: Configuration) -> None:
        """Salva configuração."""
        ...
    
    def delete_configuration(self, configuration_id: UUID) -> None:
        """Remove configuração."""
        ...


class SystemAlertRepository(Protocol):
    """Interface para repositório de alertas."""
    
    def get_all_alerts(self) -> List[SystemAlert]:
        """Obtém todos os alertas."""
        ...
    
    def get_unacknowledged_alerts(self) -> List[SystemAlert]:
        """Obtém alertas não reconhecidos."""
        ...
    
    def save_alert(self, alert: SystemAlert) -> None:
        """Salva alerta."""
        ...
    
    def delete_alert(self, alert_id: UUID) -> None:
        """Remove alerta."""
        ...


class SystemSessionRepository(Protocol):
    """Interface para repositório de sessões."""
    
    def get_current_session(self) -> Optional[SystemSession]:
        """Obtém sessão atual."""
        ...
    
    def save_session(self, session: SystemSession) -> None:
        """Salva sessão."""
        ...


# Interfaces de serviços externos
class FileSystemService(Protocol):
    """Interface para serviços de sistema de arquivos."""
    
    def get_drive_info(self, drive_letter: str) -> Optional[DriveInfo]:
        """Obtém informações de um drive."""
        ...
    
    def scan_directory(self, path: str, extensions: Set[str]) -> List[str]:
        """Escaneia diretório por arquivos com extensões específicas."""
        ...
    
    def copy_file(self, source: str, destination: str) -> bool:
        """Copia arquivo."""
        ...
    
    def move_file(self, source: str, destination: str) -> bool:
        """Move arquivo."""
        ...
    
    def create_directory(self, path: str) -> bool:
        """Cria diretório."""
        ...


class SystemMonitoringService(Protocol):
    """Interface para serviços de monitoramento."""
    
    def get_current_metrics(self) -> SystemMetrics:
        """Obtém métricas atuais do sistema."""
        ...
    
    def get_running_processes(self) -> List[str]:
        """Obtém processos em execução."""
        ...


# Resultado de casos de uso
@dataclass
class UseCaseResult:
    """Resultado de um caso de uso."""
    
    success: bool
    message: str
    data: Any = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# Casos de uso base
class UseCase(ABC):
    """Classe base para casos de uso."""
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> UseCaseResult:
        """Executa o caso de uso."""
        pass


# Casos de uso para gerenciamento de drives
class DetectDrivesUseCase(UseCase):
    """Caso de uso para detectar drives do sistema."""
    
    def __init__(self, drive_repository: DriveRepository, 
                 file_system_service: FileSystemService):
        self.drive_repository = drive_repository
        self.file_system_service = file_system_service
    
    def execute(self) -> UseCaseResult:
        """Detecta todos os drives disponíveis no sistema."""
        try:
            detected_drives = []
            
            # Detectar drives do sistema (A-Z no Windows)
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive_info = self.file_system_service.get_drive_info(f"{letter}:")
                
                if drive_info and drive_info.is_ready:
                    # Verificar se já existe no repositório
                    existing_drive = self.drive_repository.get_drive_by_letter(letter)
                    
                    if existing_drive:
                        # Atualizar informações
                        existing_drive.info = drive_info
                        self.drive_repository.save_drive(existing_drive)
                        detected_drives.append(existing_drive)
                    else:
                        # Criar novo drive
                        new_drive = Drive(info=drive_info)
                        self.drive_repository.save_drive(new_drive)
                        detected_drives.append(new_drive)
            
            return UseCaseResult(
                success=True,
                message=f"Detectados {len(detected_drives)} drives",
                data=detected_drives
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao detectar drives",
                errors=[str(e)]
            )


class SelectEmulationDriveUseCase(UseCase):
    """Caso de uso para selecionar drive de emulação."""
    
    def __init__(self, drive_repository: DriveRepository):
        self.drive_repository = drive_repository
    
    def execute(self, drive_letter: str, emulation_path: str) -> UseCaseResult:
        """Seleciona um drive como drive de emulação."""
        try:
            drive = self.drive_repository.get_drive_by_letter(drive_letter)
            
            if not drive:
                return UseCaseResult(
                    success=False,
                    message=f"Drive {drive_letter}: não encontrado"
                )
            
            # Verificar se tem espaço suficiente (pelo menos 10GB)
            min_space_gb = 10 * 1024 * 1024 * 1024  # 10GB em bytes
            if drive.info.free_space < min_space_gb:
                return UseCaseResult(
                    success=False,
                    message=f"Drive {drive_letter}: não tem espaço suficiente (mínimo 10GB)"
                )
            
            # Definir como drive de emulação
            drive.set_as_emulation_drive(emulation_path)
            self.drive_repository.save_drive(drive)
            
            return UseCaseResult(
                success=True,
                message=f"Drive {drive_letter}: configurado como drive de emulação",
                data=drive
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao configurar drive de emulação",
                errors=[str(e)]
            )


# Casos de uso para gerenciamento de emuladores
class DetectEmulatorsUseCase(UseCase):
    """Caso de uso para detectar emuladores instalados."""
    
    def __init__(self, emulator_repository: EmulatorRepository,
                 file_system_service: FileSystemService):
        self.emulator_repository = emulator_repository
        self.file_system_service = file_system_service
        
        # Mapeamento de emuladores conhecidos
        self.known_emulators = {
            "retroarch.exe": {
                "name": "RetroArch",
                "platforms": {SystemPlatform.NINTENDO_NES, SystemPlatform.NINTENDO_SNES,
                            SystemPlatform.SONY_PSX, SystemPlatform.SEGA_GENESIS}
            },
            "pcsx2.exe": {
                "name": "PCSX2",
                "platforms": {SystemPlatform.SONY_PS2}
            },
            "dolphin.exe": {
                "name": "Dolphin",
                "platforms": {SystemPlatform.NINTENDO_GAMECUBE, SystemPlatform.NINTENDO_WII}
            },
            "cemu.exe": {
                "name": "Cemu",
                "platforms": {SystemPlatform.NINTENDO_WII}
            },
            "yuzu.exe": {
                "name": "Yuzu",
                "platforms": {SystemPlatform.NINTENDO_SWITCH}
            },
            "ppsspp.exe": {
                "name": "PPSSPP",
                "platforms": {SystemPlatform.SONY_PSP}
            }
        }
    
    def execute(self, search_paths: List[str] = None) -> UseCaseResult:
        """Detecta emuladores em caminhos especificados."""
        try:
            if search_paths is None:
                # Caminhos padrão para busca
                search_paths = [
                    "C:\\Program Files",
                    "C:\\Program Files (x86)",
                    "C:\\Games",
                    "C:\\Emulators"
                ]
            
            detected_emulators = []
            
            for search_path in search_paths:
                if not Path(search_path).exists():
                    continue
                
                # Buscar executáveis conhecidos
                for executable, info in self.known_emulators.items():
                    found_files = self.file_system_service.scan_directory(
                        search_path, {executable}
                    )
                    
                    for exe_path in found_files:
                        # Verificar se já existe
                        existing = self.emulator_repository.get_emulator_by_name(info["name"])
                        
                        if not existing:
                            emulator = Emulator(
                                name=info["name"],
                                executable_path=exe_path,
                                supported_platforms=info["platforms"],
                                status=EmulatorStatus.DETECTED
                            )
                            
                            self.emulator_repository.save_emulator(emulator)
                            detected_emulators.append(emulator)
            
            return UseCaseResult(
                success=True,
                message=f"Detectados {len(detected_emulators)} emuladores",
                data=detected_emulators
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao detectar emuladores",
                errors=[str(e)]
            )


class ConfigureEmulatorUseCase(UseCase):
    """Caso de uso para configurar emulador."""
    
    def __init__(self, emulator_repository: EmulatorRepository,
                 configuration_repository: ConfigurationRepository):
        self.emulator_repository = emulator_repository
        self.configuration_repository = configuration_repository
    
    def execute(self, emulator_name: str, config_path: str, 
                config_data: Dict[str, Any]) -> UseCaseResult:
        """Configura um emulador."""
        try:
            emulator = self.emulator_repository.get_emulator_by_name(emulator_name)
            
            if not emulator:
                return UseCaseResult(
                    success=False,
                    message=f"Emulador {emulator_name} não encontrado"
                )
            
            # Atualizar caminho de configuração
            emulator.config_path = config_path
            emulator.set_status(EmulatorStatus.CONFIGURED)
            self.emulator_repository.save_emulator(emulator)
            
            # Criar configuração
            configuration = Configuration(
                name=f"{emulator_name}_default",
                emulator_name=emulator_name,
                platform=list(emulator.supported_platforms)[0],  # Primeira plataforma
                config_data=config_data
            )
            
            self.configuration_repository.save_configuration(configuration)
            
            return UseCaseResult(
                success=True,
                message=f"Emulador {emulator_name} configurado com sucesso",
                data={"emulator": emulator, "configuration": configuration}
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao configurar emulador",
                errors=[str(e)]
            )


# Casos de uso para detecção de sistemas legacy
class DetectLegacyInstallationsUseCase(UseCase):
    """Caso de uso para detectar instalações legacy."""
    
    def __init__(self, legacy_repository: LegacyInstallationRepository,
                 file_system_service: FileSystemService):
        self.legacy_repository = legacy_repository
        self.file_system_service = file_system_service
        
        # Padrões de detecção de instalações legacy
        self.legacy_patterns = {
            "RetroArch": {
                "indicators": ["retroarch.exe", "retroarch.cfg"],
                "platform": SystemPlatform.UNKNOWN
            },
            "PCSX2": {
                "indicators": ["pcsx2.exe", "inis"],
                "platform": SystemPlatform.SONY_PS2
            },
            "Project64": {
                "indicators": ["project64.exe", "Config"],
                "platform": SystemPlatform.NINTENDO_N64
            },
            "ePSXe": {
                "indicators": ["epsxe.exe", "bios"],
                "platform": SystemPlatform.SONY_PSX
            }
        }
    
    def execute(self, search_drives: List[str] = None) -> UseCaseResult:
        """Detecta instalações legacy em drives especificados."""
        try:
            if search_drives is None:
                search_drives = ["C:", "D:", "E:", "F:"]
            
            detected_installations = []
            
            for drive in search_drives:
                if not Path(drive).exists():
                    continue
                
                # Buscar por cada tipo de emulador
                for emulator_type, pattern in self.legacy_patterns.items():
                    for indicator in pattern["indicators"]:
                        found_paths = self.file_system_service.scan_directory(
                            drive, {indicator}
                        )
                        
                        for found_path in found_paths:
                            installation_path = str(Path(found_path).parent)
                            
                            # Verificar se já foi detectada
                            existing = self.legacy_repository.get_installation_by_path(
                                installation_path
                            )
                            
                            if not existing:
                                # Calcular tamanho da instalação
                                size_bytes = self._calculate_directory_size(installation_path)
                                
                                # Contar ROMs e saves
                                rom_count = self._count_roms(installation_path)
                                save_count = self._count_saves(installation_path)
                                
                                installation = LegacyInstallation(
                                    name=f"{emulator_type} ({Path(installation_path).name})",
                                    path=installation_path,
                                    platform=pattern["platform"],
                                    emulator_type=emulator_type,
                                    size_bytes=size_bytes,
                                    rom_count=rom_count,
                                    save_count=save_count
                                )
                                
                                self.legacy_repository.save_installation(installation)
                                detected_installations.append(installation)
            
            return UseCaseResult(
                success=True,
                message=f"Detectadas {len(detected_installations)} instalações legacy",
                data=detected_installations
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao detectar instalações legacy",
                errors=[str(e)]
            )
    
    def _calculate_directory_size(self, path: str) -> int:
        """Calcula tamanho de um diretório."""
        try:
            total_size = 0
            for file_path in Path(path).rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except:
            return 0
    
    def _count_roms(self, path: str) -> int:
        """Conta ROMs em um diretório."""
        rom_extensions = {".iso", ".bin", ".cue", ".img", ".nrg", ".mdf", 
                         ".nes", ".smc", ".sfc", ".n64", ".z64", ".gba", ".gbc", ".gb"}
        
        try:
            count = 0
            for file_path in Path(path).rglob("*"):
                if file_path.suffix.lower() in rom_extensions:
                    count += 1
            return count
        except:
            return 0
    
    def _count_saves(self, path: str) -> int:
        """Conta saves em um diretório."""
        save_extensions = {".sav", ".srm", ".st", ".state", ".mcr", ".ps2"}
        
        try:
            count = 0
            for file_path in Path(path).rglob("*"):
                if file_path.suffix.lower() in save_extensions:
                    count += 1
            return count
        except:
            return 0


# Casos de uso para migração
class CreateMigrationTaskUseCase(UseCase):
    """Caso de uso para criar tarefa de migração."""
    
    def __init__(self, migration_repository: MigrationTaskRepository,
                 drive_repository: DriveRepository):
        self.migration_repository = migration_repository
        self.drive_repository = drive_repository
    
    def execute(self, installation: LegacyInstallation, 
                target_drive_letter: str, target_path: str) -> UseCaseResult:
        """Cria uma nova tarefa de migração."""
        try:
            target_drive = self.drive_repository.get_drive_by_letter(target_drive_letter)
            
            if not target_drive:
                return UseCaseResult(
                    success=False,
                    message=f"Drive de destino {target_drive_letter}: não encontrado"
                )
            
            if not target_drive.is_emulation_drive:
                return UseCaseResult(
                    success=False,
                    message=f"Drive {target_drive_letter}: não está configurado como drive de emulação"
                )
            
            # Verificar espaço disponível
            if target_drive.info.free_space < installation.size_bytes:
                return UseCaseResult(
                    success=False,
                    message="Espaço insuficiente no drive de destino"
                )
            
            # Criar tarefa de migração
            migration_task = MigrationTask(
                source_installation=installation,
                target_drive=target_drive,
                target_path=target_path
            )
            
            self.migration_repository.save_task(migration_task)
            
            return UseCaseResult(
                success=True,
                message="Tarefa de migração criada com sucesso",
                data=migration_task
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao criar tarefa de migração",
                errors=[str(e)]
            )


class ExecuteMigrationUseCase(UseCase):
    """Caso de uso para executar migração."""
    
    def __init__(self, migration_repository: MigrationTaskRepository,
                 file_system_service: FileSystemService):
        self.migration_repository = migration_repository
        self.file_system_service = file_system_service
    
    def execute(self, task_id: UUID) -> UseCaseResult:
        """Executa uma tarefa de migração."""
        try:
            task = self.migration_repository.get_task_by_id(task_id)
            
            if not task:
                return UseCaseResult(
                    success=False,
                    message="Tarefa de migração não encontrada"
                )
            
            if task.status != MigrationStatus.PENDING:
                return UseCaseResult(
                    success=False,
                    message=f"Tarefa não pode ser executada. Status atual: {task.status.value}"
                )
            
            # Iniciar migração
            task.set_status(MigrationStatus.IN_PROGRESS)
            self.migration_repository.save_task(task)
            
            # Criar diretório de destino
            if not self.file_system_service.create_directory(task.target_path):
                task.set_status(MigrationStatus.FAILED, "Falha ao criar diretório de destino")
                self.migration_repository.save_task(task)
                return UseCaseResult(
                    success=False,
                    message="Falha ao criar diretório de destino"
                )
            
            # Listar arquivos para migração
            source_path = Path(task.source_installation.path)
            files_to_migrate = []
            
            for file_path in source_path.rglob("*"):
                if file_path.is_file():
                    files_to_migrate.append(str(file_path))
            
            task.files_to_migrate = files_to_migrate
            self.migration_repository.save_task(task)
            
            # Migrar arquivos
            migrated_count = 0
            total_files = len(files_to_migrate)
            
            for file_path in files_to_migrate:
                try:
                    # Calcular caminho de destino
                    relative_path = Path(file_path).relative_to(source_path)
                    destination_path = Path(task.target_path) / relative_path
                    
                    # Criar diretório pai se necessário
                    destination_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copiar arquivo
                    if self.file_system_service.copy_file(file_path, str(destination_path)):
                        task.mark_file_migrated(file_path)
                        migrated_count += 1
                        
                        # Atualizar progresso
                        progress = (migrated_count / total_files) * 100
                        task.update_progress(progress)
                        
                        # Salvar progresso a cada 10 arquivos
                        if migrated_count % 10 == 0:
                            self.migration_repository.save_task(task)
                    
                except Exception as e:
                    # Log do erro mas continua migração
                    continue
            
            # Finalizar migração
            if migrated_count == total_files:
                task.set_status(MigrationStatus.COMPLETED)
                task.update_progress(100.0)
            else:
                task.set_status(MigrationStatus.FAILED, 
                              f"Migrados {migrated_count}/{total_files} arquivos")
            
            self.migration_repository.save_task(task)
            
            return UseCaseResult(
                success=task.status == MigrationStatus.COMPLETED,
                message=f"Migração finalizada. Status: {task.status.value}",
                data=task
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro durante migração",
                errors=[str(e)]
            )


# Casos de uso para monitoramento
class MonitorSystemPerformanceUseCase(UseCase):
    """Caso de uso para monitorar performance do sistema."""
    
    def __init__(self, alert_repository: SystemAlertRepository,
                 monitoring_service: SystemMonitoringService):
        self.alert_repository = alert_repository
        self.monitoring_service = monitoring_service
        
        # Limites de alerta
        self.cpu_warning_threshold = 80.0
        self.cpu_critical_threshold = 95.0
        self.memory_warning_threshold = 85.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 85.0
        self.disk_critical_threshold = 95.0
    
    def execute(self) -> UseCaseResult:
        """Monitora performance e gera alertas se necessário."""
        try:
            metrics = self.monitoring_service.get_current_metrics()
            alerts_created = []
            
            # Verificar CPU
            if metrics.cpu_usage >= self.cpu_critical_threshold:
                alert = self._create_alert(
                    "CPU Crítica",
                    f"Uso de CPU em {metrics.cpu_usage:.1f}%",
                    AlertSeverity.CRITICAL,
                    "SystemMonitoring"
                )
                alerts_created.append(alert)
            elif metrics.cpu_usage >= self.cpu_warning_threshold:
                alert = self._create_alert(
                    "CPU Alta",
                    f"Uso de CPU em {metrics.cpu_usage:.1f}%",
                    AlertSeverity.WARNING,
                    "SystemMonitoring"
                )
                alerts_created.append(alert)
            
            # Verificar Memória
            if metrics.memory_usage >= self.memory_critical_threshold:
                alert = self._create_alert(
                    "Memória Crítica",
                    f"Uso de memória em {metrics.memory_usage:.1f}%",
                    AlertSeverity.CRITICAL,
                    "SystemMonitoring"
                )
                alerts_created.append(alert)
            elif metrics.memory_usage >= self.memory_warning_threshold:
                alert = self._create_alert(
                    "Memória Alta",
                    f"Uso de memória em {metrics.memory_usage:.1f}%",
                    AlertSeverity.WARNING,
                    "SystemMonitoring"
                )
                alerts_created.append(alert)
            
            # Verificar Disco
            if metrics.disk_usage >= self.disk_critical_threshold:
                alert = self._create_alert(
                    "Disco Crítico",
                    f"Uso de disco em {metrics.disk_usage:.1f}%",
                    AlertSeverity.CRITICAL,
                    "SystemMonitoring"
                )
                alerts_created.append(alert)
            elif metrics.disk_usage >= self.disk_warning_threshold:
                alert = self._create_alert(
                    "Disco Cheio",
                    f"Uso de disco em {metrics.disk_usage:.1f}%",
                    AlertSeverity.WARNING,
                    "SystemMonitoring"
                )
                alerts_created.append(alert)
            
            return UseCaseResult(
                success=True,
                message=f"Monitoramento concluído. {len(alerts_created)} alertas criados",
                data={"metrics": metrics, "alerts": alerts_created}
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro durante monitoramento",
                errors=[str(e)]
            )
    
    def _create_alert(self, title: str, message: str, 
                     severity: AlertSeverity, source: str) -> SystemAlert:
        """Cria um alerta do sistema."""
        alert = SystemAlert(
            title=title,
            message=message,
            severity=severity,
            source_component=source
        )
        
        self.alert_repository.save_alert(alert)
        return alert


# Casos de uso para sessão
class StartSystemSessionUseCase(UseCase):
    """Caso de uso para iniciar sessão do sistema."""
    
    def __init__(self, session_repository: SystemSessionRepository):
        self.session_repository = session_repository
    
    def execute(self, user_name: str) -> UseCaseResult:
        """Inicia uma nova sessão do sistema."""
        try:
            # Verificar se já existe sessão ativa
            current_session = self.session_repository.get_current_session()
            
            if current_session and current_session.is_active:
                return UseCaseResult(
                    success=False,
                    message="Já existe uma sessão ativa"
                )
            
            # Criar nova sessão
            session = SystemSession(
                user_name=user_name,
                start_time=datetime.now()
            )
            
            self.session_repository.save_session(session)
            
            return UseCaseResult(
                success=True,
                message=f"Sessão iniciada para {user_name}",
                data=session
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao iniciar sessão",
                errors=[str(e)]
            )


class EndSystemSessionUseCase(UseCase):
    """Caso de uso para finalizar sessão do sistema."""
    
    def __init__(self, session_repository: SystemSessionRepository):
        self.session_repository = session_repository
    
    def execute(self) -> UseCaseResult:
        """Finaliza a sessão atual do sistema."""
        try:
            current_session = self.session_repository.get_current_session()
            
            if not current_session or not current_session.is_active:
                return UseCaseResult(
                    success=False,
                    message="Não há sessão ativa para finalizar"
                )
            
            # Finalizar sessão
            current_session.end_session()
            self.session_repository.save_session(current_session)
            
            return UseCaseResult(
                success=True,
                message=f"Sessão finalizada. Duração: {current_session.duration} segundos",
                data=current_session
            )
            
        except Exception as e:
            return UseCaseResult(
                success=False,
                message="Erro ao finalizar sessão",
                errors=[str(e)]
            )