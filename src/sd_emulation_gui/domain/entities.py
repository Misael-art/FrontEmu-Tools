"""
Domain Entities

Entidades de domínio que representam os conceitos centrais do sistema
FrontEmu-Tools seguindo os princípios da Clean Architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4


class DriveType(Enum):
    """Tipos de drives suportados."""
    FIXED = "fixed"
    REMOVABLE = "removable"
    NETWORK = "network"
    CDROM = "cdrom"
    RAM = "ram"
    UNKNOWN = "unknown"


class SystemPlatform(Enum):
    """Plataformas de sistema suportadas."""
    NINTENDO_NES = "nintendo_nes"
    NINTENDO_SNES = "nintendo_snes"
    NINTENDO_N64 = "nintendo_n64"
    NINTENDO_GAMECUBE = "nintendo_gamecube"
    NINTENDO_WII = "nintendo_wii"
    NINTENDO_SWITCH = "nintendo_switch"
    NINTENDO_GB = "nintendo_gameboy"
    NINTENDO_GBC = "nintendo_gameboy_color"
    NINTENDO_GBA = "nintendo_gameboy_advance"
    NINTENDO_DS = "nintendo_ds"
    NINTENDO_3DS = "nintendo_3ds"
    SONY_PSX = "sony_playstation"
    SONY_PS2 = "sony_playstation_2"
    SONY_PS3 = "sony_playstation_3"
    SONY_PSP = "sony_psp"
    SONY_PSVITA = "sony_psvita"
    SEGA_GENESIS = "sega_genesis"
    SEGA_SATURN = "sega_saturn"
    SEGA_DREAMCAST = "sega_dreamcast"
    SEGA_GAME_GEAR = "sega_game_gear"
    ATARI_2600 = "atari_2600"
    ATARI_7800 = "atari_7800"
    ARCADE = "arcade"
    PC_DOS = "pc_dos"
    PC_WINDOWS = "pc_windows"
    PC_LINUX = "pc_linux"
    PC_MACOS = "pc_macos"
    UNKNOWN = "unknown"


class EmulatorStatus(Enum):
    """Status de um emulador."""
    DETECTED = "detected"
    CONFIGURED = "configured"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    NOT_FOUND = "not_found"


class MigrationStatus(Enum):
    """Status de migração de sistema legacy."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AlertSeverity(Enum):
    """Severidade de alertas do sistema."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ValueObject(ABC):
    """Classe base para Value Objects."""
    
    def __post_init__(self):
        """Validação após inicialização."""
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """Valida o value object."""
        pass


@dataclass(frozen=True)
class DriveInfo(ValueObject):
    """Value Object para informações de drive."""
    
    letter: str
    label: str
    drive_type: DriveType
    file_system: str
    total_space: int
    free_space: int
    used_space: int
    is_ready: bool
    
    def validate(self) -> None:
        """Valida informações do drive."""
        if not self.letter:
            raise ValueError("Drive letter cannot be empty")
        
        if self.total_space < 0:
            raise ValueError("Total space cannot be negative")
        
        if self.free_space < 0:
            raise ValueError("Free space cannot be negative")
        
        if self.used_space < 0:
            raise ValueError("Used space cannot be negative")
        
        if self.free_space + self.used_space > self.total_space:
            raise ValueError("Free + used space cannot exceed total space")
    
    @property
    def usage_percentage(self) -> float:
        """Calcula percentual de uso do drive."""
        if self.total_space == 0:
            return 0.0
        return (self.used_space / self.total_space) * 100
    
    @property
    def is_low_space(self) -> bool:
        """Verifica se o drive tem pouco espaço livre."""
        return self.usage_percentage > 85.0
    
    @property
    def is_critical_space(self) -> bool:
        """Verifica se o drive tem espaço crítico."""
        return self.usage_percentage > 95.0


@dataclass(frozen=True)
class SystemMetrics(ValueObject):
    """Value Object para métricas do sistema."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    gpu_usage: float = 0.0
    cpu_temperature: float = 0.0
    gpu_temperature: float = 0.0
    network_upload: float = 0.0
    network_download: float = 0.0
    
    def validate(self) -> None:
        """Valida métricas do sistema."""
        if not (0 <= self.cpu_usage <= 100):
            raise ValueError("CPU usage must be between 0 and 100")
        
        if not (0 <= self.memory_usage <= 100):
            raise ValueError("Memory usage must be between 0 and 100")
        
        if not (0 <= self.disk_usage <= 100):
            raise ValueError("Disk usage must be between 0 and 100")
        
        if not (0 <= self.gpu_usage <= 100):
            raise ValueError("GPU usage must be between 0 and 100")
        
        if self.cpu_temperature < -273.15:  # Absolute zero
            raise ValueError("CPU temperature cannot be below absolute zero")
        
        if self.gpu_temperature < -273.15:
            raise ValueError("GPU temperature cannot be below absolute zero")


@dataclass
class Entity(ABC):
    """Classe base para todas as entidades do domínio."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validação após inicialização."""
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """Valida a entidade."""
        pass
    
    def update_timestamp(self) -> None:
        """Atualiza timestamp de modificação."""
        self.updated_at = datetime.now()


@dataclass
class Drive(Entity):
    """Entidade que representa um drive do sistema."""
    
    info: Optional[DriveInfo] = None
    is_emulation_drive: bool = False
    emulation_path: Optional[str] = None
    detected_emulators: List[str] = field(default_factory=list)
    detected_roms: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Valida a entidade Drive."""
        if not self.info:
            raise ValueError("Drive info is required")
        
        if self.is_emulation_drive and not self.emulation_path:
            raise ValueError("Emulation drive must have emulation path")
    
    def add_detected_emulator(self, emulator_name: str) -> None:
        """Adiciona emulador detectado."""
        if emulator_name not in self.detected_emulators:
            self.detected_emulators.append(emulator_name)
            self.update_timestamp()
    
    def add_detected_rom(self, rom_path: str) -> None:
        """Adiciona ROM detectada."""
        if rom_path not in self.detected_roms:
            self.detected_roms.append(rom_path)
            self.update_timestamp()
    
    def set_as_emulation_drive(self, emulation_path: str) -> None:
        """Define como drive de emulação."""
        self.is_emulation_drive = True
        self.emulation_path = emulation_path
        self.update_timestamp()


@dataclass
class Emulator(Entity):
    """Entidade que representa um emulador."""
    
    name: str = ""
    executable_path: str = ""
    supported_platforms: Set[SystemPlatform] = field(default_factory=set)
    status: EmulatorStatus = EmulatorStatus.DETECTED
    config_path: Optional[str] = None
    version: Optional[str] = None
    cores: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Valida a entidade Emulator."""
        if not self.name:
            raise ValueError("Emulator name is required")
        
        if not self.executable_path:
            raise ValueError("Executable path is required")
        
        if not self.supported_platforms:
            raise ValueError("At least one supported platform is required")
    
    def add_supported_platform(self, platform: SystemPlatform) -> None:
        """Adiciona plataforma suportada."""
        self.supported_platforms.add(platform)
        self.update_timestamp()
    
    def set_status(self, status: EmulatorStatus) -> None:
        """Define status do emulador."""
        self.status = status
        self.update_timestamp()
    
    def add_core(self, core_name: str) -> None:
        """Adiciona core (para RetroArch)."""
        if core_name not in self.cores:
            self.cores.append(core_name)
            self.update_timestamp()
    
    def supports_platform(self, platform: SystemPlatform) -> bool:
        """Verifica se suporta uma plataforma."""
        return platform in self.supported_platforms


@dataclass
class LegacyInstallation(Entity):
    """Entidade que representa uma instalação legacy detectada."""
    
    name: str = ""
    path: str = ""
    platform: SystemPlatform = SystemPlatform.PC_WINDOWS
    emulator_type: str = ""
    size_bytes: int = 0
    rom_count: int = 0
    save_count: int = 0
    config_files: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Valida a entidade LegacyInstallation."""
        if not self.name:
            raise ValueError("Installation name is required")
        
        if not self.path:
            raise ValueError("Installation path is required")
        
        if not Path(self.path).exists():
            raise ValueError(f"Installation path does not exist: {self.path}")
        
        if self.size_bytes < 0:
            raise ValueError("Size cannot be negative")
        
        if self.rom_count < 0:
            raise ValueError("ROM count cannot be negative")
        
        if self.save_count < 0:
            raise ValueError("Save count cannot be negative")
    
    def add_config_file(self, config_path: str) -> None:
        """Adiciona arquivo de configuração."""
        if config_path not in self.config_files:
            self.config_files.append(config_path)
            self.update_timestamp()
    
    def update_counts(self, rom_count: int, save_count: int) -> None:
        """Atualiza contadores de ROMs e saves."""
        self.rom_count = max(0, rom_count)
        self.save_count = max(0, save_count)
        self.update_timestamp()


@dataclass
class MigrationTask(Entity):
    """Entidade que representa uma tarefa de migração."""
    
    source_installation: Optional[LegacyInstallation] = None
    target_drive: Optional[Drive] = None
    target_path: str = ""
    status: MigrationStatus = MigrationStatus.PENDING
    progress_percentage: float = 0.0
    estimated_time_remaining: Optional[int] = None  # segundos
    error_message: Optional[str] = None
    files_to_migrate: List[str] = field(default_factory=list)
    migrated_files: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Valida a entidade MigrationTask."""
        if not self.source_installation:
            raise ValueError("Source installation is required")
        
        if not self.target_drive:
            raise ValueError("Target drive is required")
        
        if not self.target_path:
            raise ValueError("Target path is required")
        
        if not (0 <= self.progress_percentage <= 100):
            raise ValueError("Progress percentage must be between 0 and 100")
    
    def set_status(self, status: MigrationStatus, error_message: Optional[str] = None) -> None:
        """Define status da migração."""
        self.status = status
        self.error_message = error_message
        self.update_timestamp()
    
    def update_progress(self, percentage: float, estimated_time: Optional[int] = None) -> None:
        """Atualiza progresso da migração."""
        self.progress_percentage = max(0, min(100, percentage))
        self.estimated_time_remaining = estimated_time
        self.update_timestamp()
    
    def add_file_to_migrate(self, file_path: str) -> None:
        """Adiciona arquivo para migração."""
        if file_path not in self.files_to_migrate:
            self.files_to_migrate.append(file_path)
            self.update_timestamp()
    
    def mark_file_migrated(self, file_path: str) -> None:
        """Marca arquivo como migrado."""
        if file_path not in self.migrated_files:
            self.migrated_files.append(file_path)
            # Atualizar progresso baseado em arquivos migrados
            if self.files_to_migrate:
                progress = (len(self.migrated_files) / len(self.files_to_migrate)) * 100
                self.update_progress(progress)


@dataclass
class SystemAlert(Entity):
    """Entidade que representa um alerta do sistema."""
    
    title: str = ""
    message: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    source_component: str = ""
    is_acknowledged: bool = False
    auto_resolve: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Valida a entidade SystemAlert."""
        if not self.title:
            raise ValueError("Alert title is required")
        
        if not self.message:
            raise ValueError("Alert message is required")
        
        if not self.source_component:
            raise ValueError("Source component is required")
    
    def acknowledge(self) -> None:
        """Reconhece o alerta."""
        self.is_acknowledged = True
        self.update_timestamp()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Adiciona metadados ao alerta."""
        self.metadata[key] = value
        self.update_timestamp()


@dataclass
class Configuration(Entity):
    """Entidade que representa uma configuração do sistema."""
    
    name: str = ""
    emulator_name: str = ""
    platform: SystemPlatform = SystemPlatform.PC_WINDOWS
    config_data: Dict[str, Any] = field(default_factory=dict)
    is_template: bool = False
    description: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    
    def validate(self) -> None:
        """Valida a entidade Configuration."""
        if not self.name:
            raise ValueError("Configuration name is required")
        
        if not self.emulator_name:
            raise ValueError("Emulator name is required")
        
        if not self.config_data:
            raise ValueError("Configuration data is required")
    
    def add_tag(self, tag: str) -> None:
        """Adiciona tag à configuração."""
        self.tags.add(tag)
        self.update_timestamp()
    
    def remove_tag(self, tag: str) -> None:
        """Remove tag da configuração."""
        self.tags.discard(tag)
        self.update_timestamp()
    
    def update_config_data(self, key: str, value: Any) -> None:
        """Atualiza dados de configuração."""
        self.config_data[key] = value
        self.update_timestamp()
    
    def has_tag(self, tag: str) -> bool:
        """Verifica se tem uma tag específica."""
        return tag in self.tags


@dataclass
class SystemSession(Entity):
    """Entidade que representa uma sessão do sistema."""
    
    user_name: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    active_emulators: List[str] = field(default_factory=list)
    performed_migrations: List[str] = field(default_factory=list)
    system_alerts: List[str] = field(default_factory=list)
    metrics_collected: int = 0
    
    def validate(self) -> None:
        """Valida a entidade SystemSession."""
        if not self.user_name:
            raise ValueError("User name is required")
        
        if self.end_time and self.end_time < self.start_time:
            raise ValueError("End time cannot be before start time")
    
    def end_session(self) -> None:
        """Finaliza a sessão."""
        self.end_time = datetime.now()
        self.update_timestamp()
    
    def add_active_emulator(self, emulator_name: str) -> None:
        """Adiciona emulador ativo."""
        if emulator_name not in self.active_emulators:
            self.active_emulators.append(emulator_name)
            self.update_timestamp()
    
    def remove_active_emulator(self, emulator_name: str) -> None:
        """Remove emulador ativo."""
        if emulator_name in self.active_emulators:
            self.active_emulators.remove(emulator_name)
            self.update_timestamp()
    
    def add_migration(self, migration_id: str) -> None:
        """Adiciona migração realizada."""
        if migration_id not in self.performed_migrations:
            self.performed_migrations.append(migration_id)
            self.update_timestamp()
    
    def add_alert(self, alert_id: str) -> None:
        """Adiciona alerta à sessão."""
        if alert_id not in self.system_alerts:
            self.system_alerts.append(alert_id)
            self.update_timestamp()
    
    def increment_metrics_collected(self) -> None:
        """Incrementa contador de métricas coletadas."""
        self.metrics_collected += 1
        self.update_timestamp()
    
    @property
    def duration(self) -> Optional[int]:
        """Duração da sessão em segundos."""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None
    
    @property
    def is_active(self) -> bool:
        """Verifica se a sessão está ativa."""
        return self.end_time is None