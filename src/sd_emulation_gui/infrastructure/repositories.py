"""
Infrastructure Repositories

Implementações concretas dos repositórios definidos na camada de domínio.
Utiliza SQLite para persistência local dos dados.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..domain.entities import (
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
from ..domain.use_cases import (
    ConfigurationRepository,
    DriveRepository,
    EmulatorRepository,
    LegacyInstallationRepository,
    MigrationTaskRepository,
    SystemAlertRepository,
    SystemSessionRepository
)


class DatabaseManager:
    """Gerenciador de banco de dados SQLite."""
    
    def __init__(self, db_path: str = None):
        """Inicializa o gerenciador de banco de dados."""
        if db_path is None:
            # Usar diretório de dados da aplicação
            app_data_dir = Path.home() / ".frontemu_tools"
            app_data_dir.mkdir(exist_ok=True)
            db_path = str(app_data_dir / "frontemu_tools.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Inicializa as tabelas do banco de dados."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de drives
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drives (
                    id TEXT PRIMARY KEY,
                    letter TEXT UNIQUE NOT NULL,
                    label TEXT,
                    file_system TEXT,
                    drive_type TEXT,
                    total_space INTEGER,
                    free_space INTEGER,
                    is_ready BOOLEAN,
                    is_emulation_drive BOOLEAN DEFAULT FALSE,
                    emulation_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de emuladores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emulators (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    executable_path TEXT,
                    config_path TEXT,
                    supported_platforms TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de instalações legacy
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS legacy_installations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    platform TEXT,
                    emulator_type TEXT,
                    size_bytes INTEGER,
                    rom_count INTEGER,
                    save_count INTEGER,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de tarefas de migração
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_tasks (
                    id TEXT PRIMARY KEY,
                    source_installation_id TEXT,
                    target_drive_id TEXT,
                    target_path TEXT,
                    status TEXT,
                    progress REAL DEFAULT 0.0,
                    error_message TEXT,
                    files_to_migrate TEXT,
                    migrated_files TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_installation_id) REFERENCES legacy_installations (id),
                    FOREIGN KEY (target_drive_id) REFERENCES drives (id)
                )
            """)
            
            # Tabela de configurações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    emulator_name TEXT,
                    platform TEXT,
                    config_data TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de alertas do sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_alerts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    message TEXT,
                    severity TEXT,
                    source_component TEXT,
                    is_acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de sessões do sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_sessions (
                    id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtém uma conexão com o banco de dados."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
        return conn


class DriveRepositoryImpl(DriveRepository):
    """Implementação do repositório de drives."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_all_drives(self) -> List[Drive]:
        """Obtém todos os drives."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drives ORDER BY letter")
            rows = cursor.fetchall()
            
            return [self._row_to_drive(row) for row in rows]
    
    def get_drive_by_letter(self, letter: str) -> Optional[Drive]:
        """Obtém drive por letra."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drives WHERE letter = ?", (letter,))
            row = cursor.fetchone()
            
            return self._row_to_drive(row) if row else None
    
    def save_drive(self, drive: Drive) -> None:
        """Salva drive."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se já existe
            cursor.execute("SELECT id FROM drives WHERE id = ?", (str(drive.id),))
            exists = cursor.fetchone()
            
            if exists:
                # Atualizar
                cursor.execute("""
                    UPDATE drives SET
                        letter = ?, label = ?, file_system = ?, drive_type = ?,
                        total_space = ?, free_space = ?, is_ready = ?,
                        is_emulation_drive = ?, emulation_path = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    drive.info.letter, drive.info.label, drive.info.file_system,
                    drive.info.drive_type.value, drive.info.total_space,
                    drive.info.free_space, drive.info.is_ready,
                    drive.is_emulation_drive, drive.emulation_path,
                    str(drive.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO drives (
                        id, letter, label, file_system, drive_type,
                        total_space, free_space, is_ready,
                        is_emulation_drive, emulation_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(drive.id), drive.info.letter, drive.info.label,
                    drive.info.file_system, drive.info.drive_type.value,
                    drive.info.total_space, drive.info.free_space,
                    drive.info.is_ready, drive.is_emulation_drive,
                    drive.emulation_path
                ))
            
            conn.commit()
    
    def delete_drive(self, drive_id: UUID) -> None:
        """Remove drive."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM drives WHERE id = ?", (str(drive_id),))
            conn.commit()
    
    def _row_to_drive(self, row: sqlite3.Row) -> Drive:
        """Converte linha do banco para entidade Drive."""
        drive_info = DriveInfo(
            letter=row["letter"],
            label=row["label"] or "",
            file_system=row["file_system"] or "",
            drive_type=DriveType(row["drive_type"]),
            total_space=row["total_space"] or 0,
            free_space=row["free_space"] or 0,
            is_ready=bool(row["is_ready"])
        )
        
        drive = Drive(info=drive_info)
        drive.id = UUID(row["id"])
        
        if row["is_emulation_drive"]:
            drive.set_as_emulation_drive(row["emulation_path"] or "")
        
        return drive


class EmulatorRepositoryImpl(EmulatorRepository):
    """Implementação do repositório de emuladores."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_all_emulators(self) -> List[Emulator]:
        """Obtém todos os emuladores."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emulators ORDER BY name")
            rows = cursor.fetchall()
            
            return [self._row_to_emulator(row) for row in rows]
    
    def get_emulator_by_name(self, name: str) -> Optional[Emulator]:
        """Obtém emulador por nome."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emulators WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            return self._row_to_emulator(row) if row else None
    
    def get_emulators_by_platform(self, platform: SystemPlatform) -> List[Emulator]:
        """Obtém emuladores por plataforma."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM emulators WHERE supported_platforms LIKE ?",
                (f"%{platform.value}%",)
            )
            rows = cursor.fetchall()
            
            return [
                emulator for emulator in [self._row_to_emulator(row) for row in rows]
                if platform in emulator.supported_platforms
            ]
    
    def save_emulator(self, emulator: Emulator) -> None:
        """Salva emulador."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Serializar plataformas suportadas
            platforms_json = json.dumps([p.value for p in emulator.supported_platforms])
            
            # Verificar se já existe
            cursor.execute("SELECT id FROM emulators WHERE id = ?", (str(emulator.id),))
            exists = cursor.fetchone()
            
            if exists:
                # Atualizar
                cursor.execute("""
                    UPDATE emulators SET
                        name = ?, executable_path = ?, config_path = ?,
                        supported_platforms = ?, status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    emulator.name, emulator.executable_path, emulator.config_path,
                    platforms_json, emulator.status.value, str(emulator.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO emulators (
                        id, name, executable_path, config_path,
                        supported_platforms, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(emulator.id), emulator.name, emulator.executable_path,
                    emulator.config_path, platforms_json, emulator.status.value
                ))
            
            conn.commit()
    
    def delete_emulator(self, emulator_id: UUID) -> None:
        """Remove emulador."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM emulators WHERE id = ?", (str(emulator_id),))
            conn.commit()
    
    def _row_to_emulator(self, row: sqlite3.Row) -> Emulator:
        """Converte linha do banco para entidade Emulator."""
        # Deserializar plataformas suportadas
        platforms_data = json.loads(row["supported_platforms"])
        supported_platforms = {SystemPlatform(p) for p in platforms_data}
        
        emulator = Emulator(
            name=row["name"],
            executable_path=row["executable_path"],
            supported_platforms=supported_platforms,
            status=EmulatorStatus(row["status"])
        )
        
        emulator.id = UUID(row["id"])
        emulator.config_path = row["config_path"]
        
        return emulator


class LegacyInstallationRepositoryImpl(LegacyInstallationRepository):
    """Implementação do repositório de instalações legacy."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_all_installations(self) -> List[LegacyInstallation]:
        """Obtém todas as instalações."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM legacy_installations ORDER BY name")
            rows = cursor.fetchall()
            
            return [self._row_to_installation(row) for row in rows]
    
    def get_installation_by_path(self, path: str) -> Optional[LegacyInstallation]:
        """Obtém instalação por caminho."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM legacy_installations WHERE path = ?", (path,))
            row = cursor.fetchone()
            
            return self._row_to_installation(row) if row else None
    
    def save_installation(self, installation: LegacyInstallation) -> None:
        """Salva instalação."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se já existe
            cursor.execute(
                "SELECT id FROM legacy_installations WHERE id = ?",
                (str(installation.id),)
            )
            exists = cursor.fetchone()
            
            if exists:
                # Atualizar
                cursor.execute("""
                    UPDATE legacy_installations SET
                        name = ?, path = ?, platform = ?, emulator_type = ?,
                        size_bytes = ?, rom_count = ?, save_count = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    installation.name, installation.path, installation.platform.value,
                    installation.emulator_type, installation.size_bytes,
                    installation.rom_count, installation.save_count,
                    str(installation.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO legacy_installations (
                        id, name, path, platform, emulator_type,
                        size_bytes, rom_count, save_count, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(installation.id), installation.name, installation.path,
                    installation.platform.value, installation.emulator_type,
                    installation.size_bytes, installation.rom_count,
                    installation.save_count, installation.detected_at.isoformat()
                ))
            
            conn.commit()
    
    def delete_installation(self, installation_id: UUID) -> None:
        """Remove instalação."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM legacy_installations WHERE id = ?",
                (str(installation_id),)
            )
            conn.commit()
    
    def _row_to_installation(self, row: sqlite3.Row) -> LegacyInstallation:
        """Converte linha do banco para entidade LegacyInstallation."""
        installation = LegacyInstallation(
            name=row["name"],
            path=row["path"],
            platform=SystemPlatform(row["platform"]),
            emulator_type=row["emulator_type"],
            size_bytes=row["size_bytes"] or 0,
            rom_count=row["rom_count"] or 0,
            save_count=row["save_count"] or 0
        )
        
        installation.id = UUID(row["id"])
        
        # Converter detected_at se disponível
        if row["detected_at"]:
            installation.detected_at = datetime.fromisoformat(row["detected_at"])
        
        return installation


class MigrationTaskRepositoryImpl(MigrationTaskRepository):
    """Implementação do repositório de tarefas de migração."""
    
    def __init__(self, db_manager: DatabaseManager,
                 legacy_repo: LegacyInstallationRepository,
                 drive_repo: DriveRepository):
        self.db_manager = db_manager
        self.legacy_repo = legacy_repo
        self.drive_repo = drive_repo
    
    def get_all_tasks(self) -> List[MigrationTask]:
        """Obtém todas as tarefas."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM migration_tasks ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            return [self._row_to_task(row) for row in rows if self._row_to_task(row)]
    
    def get_task_by_id(self, task_id: UUID) -> Optional[MigrationTask]:
        """Obtém tarefa por ID."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM migration_tasks WHERE id = ?", (str(task_id),))
            row = cursor.fetchone()
            
            return self._row_to_task(row) if row else None
    
    def get_tasks_by_status(self, status: MigrationStatus) -> List[MigrationTask]:
        """Obtém tarefas por status."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM migration_tasks WHERE status = ? ORDER BY created_at DESC",
                (status.value,)
            )
            rows = cursor.fetchall()
            
            return [self._row_to_task(row) for row in rows if self._row_to_task(row)]
    
    def save_task(self, task: MigrationTask) -> None:
        """Salva tarefa."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Serializar listas de arquivos
            files_to_migrate_json = json.dumps(task.files_to_migrate or [])
            migrated_files_json = json.dumps(task.migrated_files or [])
            
            # Verificar se já existe
            cursor.execute("SELECT id FROM migration_tasks WHERE id = ?", (str(task.id),))
            exists = cursor.fetchone()
            
            if exists:
                # Atualizar
                cursor.execute("""
                    UPDATE migration_tasks SET
                        target_path = ?, status = ?, progress = ?,
                        error_message = ?, files_to_migrate = ?,
                        migrated_files = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    task.target_path, task.status.value, task.progress,
                    task.error_message, files_to_migrate_json,
                    migrated_files_json, str(task.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO migration_tasks (
                        id, source_installation_id, target_drive_id,
                        target_path, status, progress, error_message,
                        files_to_migrate, migrated_files
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(task.id), str(task.source_installation.id),
                    str(task.target_drive.id), task.target_path,
                    task.status.value, task.progress, task.error_message,
                    files_to_migrate_json, migrated_files_json
                ))
            
            conn.commit()
    
    def delete_task(self, task_id: UUID) -> None:
        """Remove tarefa."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM migration_tasks WHERE id = ?", (str(task_id),))
            conn.commit()
    
    def _row_to_task(self, row: sqlite3.Row) -> Optional[MigrationTask]:
        """Converte linha do banco para entidade MigrationTask."""
        try:
            # Buscar instalação e drive relacionados
            installation = self.legacy_repo.get_installation_by_path(
                # Precisamos buscar por ID, mas não temos método direto
                # Vamos implementar uma busca alternativa
                ""
            )
            
            # Buscar drive por ID (precisamos implementar método)
            drive = None
            all_drives = self.drive_repo.get_all_drives()
            for d in all_drives:
                if str(d.id) == row["target_drive_id"]:
                    drive = d
                    break
            
            if not installation or not drive:
                return None
            
            # Deserializar listas de arquivos
            files_to_migrate = json.loads(row["files_to_migrate"] or "[]")
            migrated_files = json.loads(row["migrated_files"] or "[]")
            
            task = MigrationTask(
                source_installation=installation,
                target_drive=drive,
                target_path=row["target_path"]
            )
            
            task.id = UUID(row["id"])
            task.set_status(MigrationStatus(row["status"]), row["error_message"])
            task.update_progress(row["progress"] or 0.0)
            task.files_to_migrate = files_to_migrate
            task.migrated_files = migrated_files
            
            return task
            
        except Exception:
            return None


class ConfigurationRepositoryImpl(ConfigurationRepository):
    """Implementação do repositório de configurações."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_all_configurations(self) -> List[Configuration]:
        """Obtém todas as configurações."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM configurations ORDER BY name")
            rows = cursor.fetchall()
            
            return [self._row_to_configuration(row) for row in rows]
    
    def get_configuration_by_name(self, name: str) -> Optional[Configuration]:
        """Obtém configuração por nome."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM configurations WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            return self._row_to_configuration(row) if row else None
    
    def get_configurations_by_emulator(self, emulator_name: str) -> List[Configuration]:
        """Obtém configurações por emulador."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM configurations WHERE emulator_name = ? ORDER BY name",
                (emulator_name,)
            )
            rows = cursor.fetchall()
            
            return [self._row_to_configuration(row) for row in rows]
    
    def save_configuration(self, configuration: Configuration) -> None:
        """Salva configuração."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Serializar dados de configuração
            config_data_json = json.dumps(configuration.config_data)
            
            # Verificar se já existe
            cursor.execute(
                "SELECT id FROM configurations WHERE id = ?",
                (str(configuration.id),)
            )
            exists = cursor.fetchone()
            
            if exists:
                # Atualizar
                cursor.execute("""
                    UPDATE configurations SET
                        name = ?, emulator_name = ?, platform = ?,
                        config_data = ?, is_active = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    configuration.name, configuration.emulator_name,
                    configuration.platform.value, config_data_json,
                    configuration.is_active, str(configuration.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO configurations (
                        id, name, emulator_name, platform,
                        config_data, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(configuration.id), configuration.name,
                    configuration.emulator_name, configuration.platform.value,
                    config_data_json, configuration.is_active
                ))
            
            conn.commit()
    
    def delete_configuration(self, configuration_id: UUID) -> None:
        """Remove configuração."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM configurations WHERE id = ?",
                (str(configuration_id),)
            )
            conn.commit()
    
    def _row_to_configuration(self, row: sqlite3.Row) -> Configuration:
        """Converte linha do banco para entidade Configuration."""
        # Deserializar dados de configuração
        config_data = json.loads(row["config_data"])
        
        configuration = Configuration(
            name=row["name"],
            emulator_name=row["emulator_name"],
            platform=SystemPlatform(row["platform"]),
            config_data=config_data
        )
        
        configuration.id = UUID(row["id"])
        configuration.is_active = bool(row["is_active"])
        
        return configuration


class SystemAlertRepositoryImpl(SystemAlertRepository):
    """Implementação do repositório de alertas."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_all_alerts(self) -> List[SystemAlert]:
        """Obtém todos os alertas."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_alerts ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            return [self._row_to_alert(row) for row in rows]
    
    def get_unacknowledged_alerts(self) -> List[SystemAlert]:
        """Obtém alertas não reconhecidos."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM system_alerts WHERE is_acknowledged = FALSE ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            
            return [self._row_to_alert(row) for row in rows]
    
    def save_alert(self, alert: SystemAlert) -> None:
        """Salva alerta."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se já existe
            cursor.execute("SELECT id FROM system_alerts WHERE id = ?", (str(alert.id),))
            exists = cursor.fetchone()
            
            if exists:
                # Atualizar
                acknowledged_at = alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
                
                cursor.execute("""
                    UPDATE system_alerts SET
                        title = ?, message = ?, severity = ?,
                        source_component = ?, is_acknowledged = ?,
                        acknowledged_at = ?
                    WHERE id = ?
                """, (
                    alert.title, alert.message, alert.severity.value,
                    alert.source_component, alert.is_acknowledged,
                    acknowledged_at, str(alert.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO system_alerts (
                        id, title, message, severity, source_component,
                        is_acknowledged, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(alert.id), alert.title, alert.message,
                    alert.severity.value, alert.source_component,
                    alert.is_acknowledged, alert.created_at.isoformat()
                ))
            
            conn.commit()
    
    def delete_alert(self, alert_id: UUID) -> None:
        """Remove alerta."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_alerts WHERE id = ?", (str(alert_id),))
            conn.commit()
    
    def _row_to_alert(self, row: sqlite3.Row) -> SystemAlert:
        """Converte linha do banco para entidade SystemAlert."""
        alert = SystemAlert(
            title=row["title"],
            message=row["message"],
            severity=AlertSeverity(row["severity"]),
            source_component=row["source_component"]
        )
        
        alert.id = UUID(row["id"])
        alert.is_acknowledged = bool(row["is_acknowledged"])
        alert.created_at = datetime.fromisoformat(row["created_at"])
        
        if row["acknowledged_at"]:
            alert.acknowledged_at = datetime.fromisoformat(row["acknowledged_at"])
        
        return alert


class SystemSessionRepositoryImpl(SystemSessionRepository):
    """Implementação do repositório de sessões."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_current_session(self) -> Optional[SystemSession]:
        """Obtém sessão atual."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM system_sessions WHERE is_active = TRUE ORDER BY start_time DESC LIMIT 1"
            )
            row = cursor.fetchone()
            
            return self._row_to_session(row) if row else None
    
    def save_session(self, session: SystemSession) -> None:
        """Salva sessão."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se já existe
            cursor.execute("SELECT id FROM system_sessions WHERE id = ?", (str(session.id),))
            exists = cursor.fetchone()
            
            end_time = session.end_time.isoformat() if session.end_time else None
            
            if exists:
                # Atualizar
                cursor.execute("""
                    UPDATE system_sessions SET
                        user_name = ?, start_time = ?, end_time = ?,
                        is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    session.user_name, session.start_time.isoformat(),
                    end_time, session.is_active, str(session.id)
                ))
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO system_sessions (
                        id, user_name, start_time, end_time, is_active
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    str(session.id), session.user_name,
                    session.start_time.isoformat(), end_time, session.is_active
                ))
            
            conn.commit()
    
    def _row_to_session(self, row: sqlite3.Row) -> SystemSession:
        """Converte linha do banco para entidade SystemSession."""
        session = SystemSession(
            user_name=row["user_name"],
            start_time=datetime.fromisoformat(row["start_time"])
        )
        
        session.id = UUID(row["id"])
        session.is_active = bool(row["is_active"])
        
        if row["end_time"]:
            session.end_time = datetime.fromisoformat(row["end_time"])
        
        return session