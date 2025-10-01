"""
Drive Detection Service

Serviço responsável pela detecção automática de drives do sistema,
seguindo os requisitos RF001 e RF002 do DRS FrontEmu-Tools.
"""

import asyncio
import logging
import platform
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil

from sd_emulation_gui.utils.base_service import BaseService
from sd_emulation_gui.utils.drive_utils import DriveUtils
from sd_emulation_gui.utils.system_utils import SystemUtils


class DriveInfo:
    """Informações detalhadas de um drive do sistema."""
    
    def __init__(self, letter: str, label: str = "", file_system: str = "",
                 total_space: int = 0, free_space: int = 0, used_space: int = 0,
                 drive_type: str = "unknown", is_ready: bool = True,
                 mount_point: str = "", device: str = ""):
        """Inicializa informações do drive.
        
        Args:
            letter: Letra do drive (ex: 'C:', 'D:')
            label: Rótulo do drive
            file_system: Sistema de arquivos (NTFS, FAT32, etc.)
            total_space: Espaço total em bytes
            free_space: Espaço livre em bytes
            used_space: Espaço usado em bytes
            drive_type: Tipo do drive (fixed, removable, network, etc.)
            is_ready: Se o drive está pronto para uso
            mount_point: Ponto de montagem
            device: Dispositivo físico
        """
        self.letter = letter
        self.label = label
        self.file_system = file_system
        self.total_space = total_space
        self.free_space = free_space
        self.used_space = used_space
        self.drive_type = drive_type
        self.is_ready = is_ready
        self.mount_point = mount_point
        self.device = device
        self.usage_percentage = (used_space / total_space * 100) if total_space > 0 else 0
        self.last_updated = datetime.now()
        
    def is_suitable_for_emulation(self, min_free_gb: float = 10.0) -> bool:
        """Verifica se o drive é adequado para instalação de emulação.
        
        Args:
            min_free_gb: Espaço mínimo livre em GB
            
        Returns:
            True se o drive é adequado
        """
        min_free_bytes = min_free_gb * 1024 * 1024 * 1024
        
        return (
            self.is_ready and
            self.drive_type in ["fixed", "ssd"] and
            self.free_space >= min_free_bytes and
            self.usage_percentage < 90 and
            self.file_system in ["NTFS", "exFAT"]
        )
        
    def get_health_status(self) -> str:
        """Retorna o status de saúde do drive baseado no uso.
        
        Returns:
            Status: 'excellent', 'good', 'warning', 'critical'
        """
        if self.usage_percentage < 70:
            return "excellent"
        elif self.usage_percentage < 85:
            return "good"
        elif self.usage_percentage < 95:
            return "warning"
        else:
            return "critical"
            
    def to_dict(self) -> Dict:
        """Converte informações do drive para dicionário."""
        return {
            'letter': self.letter,
            'label': self.label,
            'file_system': self.file_system,
            'total_space': self.total_space,
            'free_space': self.free_space,
            'used_space': self.used_space,
            'usage_percentage': round(self.usage_percentage, 2),
            'drive_type': self.drive_type,
            'is_ready': self.is_ready,
            'mount_point': self.mount_point,
            'device': self.device,
            'health_status': self.get_health_status(),
            'suitable_for_emulation': self.is_suitable_for_emulation(),
            'total_space_formatted': DriveUtils.format_bytes(self.total_space),
            'free_space_formatted': DriveUtils.format_bytes(self.free_space),
            'used_space_formatted': DriveUtils.format_bytes(self.used_space),
            'last_updated': self.last_updated.isoformat()
        }


class DriveDetectionService(BaseService):
    """Serviço para detecção automática de drives do sistema."""
    
    def __init__(self):
        """Inicializa o serviço de detecção de drives."""
        # Cache de drives detectados
        self._drives_cache: Dict[str, DriveInfo] = {}
        self._cache_timestamp = None
        self._cache_duration = 10  # Cache válido por 10 segundos
        
        # Configurações
        self.min_free_space_gb = 10.0  # Mínimo de 10GB para emulação
        self.supported_filesystems = ["NTFS", "exFAT", "FAT32"]
        self.preferred_drive_types = ["fixed", "ssd"]
        
        # Callbacks para notificações
        self._drive_change_callbacks = []
        
        super().__init__()
        
    def initialize(self) -> None:
        """Inicializa o serviço de detecção de drives."""
        try:
            self.logger.info("Inicializando DriveDetectionService...")
            
            # Verificar se psutil está disponível
            if not hasattr(psutil, 'disk_partitions'):
                raise ImportError("psutil não está disponível ou incompleto")
            
            # Detectar drives iniciais
            self._refresh_drives_cache()
            
            self.logger.info(f"DriveDetectionService inicializado. {len(self._drives_cache)} drives detectados")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar DriveDetectionService: {e}")
            raise
    
    def get_all_drives(self, force_refresh: bool = False) -> Dict[str, DriveInfo]:
        """Obtém todos os drives detectados no sistema.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            Dicionário com informações dos drives
        """
        if force_refresh or not self._is_cache_valid():
            self._refresh_drives_cache()
        
        return self._drives_cache.copy()
    
    def get_drive_info(self, drive_letter: str, force_refresh: bool = False) -> Optional[DriveInfo]:
        """Obtém informações de um drive específico.
        
        Args:
            drive_letter: Letra do drive (ex: 'C:', 'D:')
            force_refresh: Força atualização do cache
            
        Returns:
            Informações do drive ou None se não encontrado
        """
        drives = self.get_all_drives(force_refresh)
        return drives.get(drive_letter.upper())
    
    def get_suitable_drives(self, min_free_gb: Optional[float] = None) -> List[DriveInfo]:
        """Obtém drives adequados para instalação de emulação.
        
        Args:
            min_free_gb: Espaço mínimo livre em GB (usa padrão se None)
            
        Returns:
            Lista de drives adequados
        """
        if min_free_gb is None:
            min_free_gb = self.min_free_space_gb
            
        drives = self.get_all_drives()
        suitable_drives = []
        
        for drive_info in drives.values():
            if drive_info.is_suitable_for_emulation(min_free_gb):
                suitable_drives.append(drive_info)
        
        # Ordenar por espaço livre (maior primeiro)
        suitable_drives.sort(key=lambda d: d.free_space, reverse=True)
        
        return suitable_drives
    
    def get_recommended_drive(self) -> Optional[DriveInfo]:
        """Obtém o drive recomendado para instalação de emulação.
        
        Returns:
            Drive recomendado ou None se nenhum adequado
        """
        suitable_drives = self.get_suitable_drives()
        
        if not suitable_drives:
            return None
        
        # Priorizar drives com mais espaço livre e melhor performance
        best_drive = suitable_drives[0]
        
        for drive in suitable_drives[1:]:
            # Preferir SSDs sobre HDDs
            if drive.drive_type == "ssd" and best_drive.drive_type != "ssd":
                best_drive = drive
            # Se ambos são do mesmo tipo, preferir o com mais espaço
            elif drive.drive_type == best_drive.drive_type and drive.free_space > best_drive.free_space:
                best_drive = drive
        
        return best_drive
    
    def validate_drive_for_emulation(self, drive_letter: str) -> Tuple[bool, List[str]]:
        """Valida se um drive é adequado para instalação de emulação.
        
        Args:
            drive_letter: Letra do drive a validar
            
        Returns:
            Tupla (é_válido, lista_de_problemas)
        """
        drive_info = self.get_drive_info(drive_letter, force_refresh=True)
        
        if not drive_info:
            return False, [f"Drive {drive_letter} não encontrado"]
        
        problems = []
        
        # Verificar se o drive está pronto
        if not drive_info.is_ready:
            problems.append("Drive não está pronto para uso")
        
        # Verificar tipo do drive
        if drive_info.drive_type not in self.preferred_drive_types:
            problems.append(f"Tipo de drive '{drive_info.drive_type}' não é recomendado")
        
        # Verificar sistema de arquivos
        if drive_info.file_system not in self.supported_filesystems:
            problems.append(f"Sistema de arquivos '{drive_info.file_system}' não é suportado")
        
        # Verificar espaço livre
        min_bytes = self.min_free_space_gb * 1024 * 1024 * 1024
        if drive_info.free_space < min_bytes:
            problems.append(f"Espaço livre insuficiente (mínimo: {self.min_free_space_gb}GB)")
        
        # Verificar uso do disco
        if drive_info.usage_percentage > 90:
            problems.append("Drive está muito cheio (>90% de uso)")
        
        # Verificar permissões de escrita
        try:
            test_path = Path(drive_letter) / "test_write_permission.tmp"
            test_path.write_text("test")
            test_path.unlink()
        except Exception:
            problems.append("Sem permissões de escrita no drive")
        
        return len(problems) == 0, problems
    
    def monitor_drive_changes(self, callback) -> None:
        """Registra callback para notificações de mudanças nos drives.
        
        Args:
            callback: Função a ser chamada quando drives mudarem
        """
        if callback not in self._drive_change_callbacks:
            self._drive_change_callbacks.append(callback)
    
    def stop_monitoring(self, callback) -> None:
        """Remove callback de monitoramento.
        
        Args:
            callback: Função a ser removida
        """
        if callback in self._drive_change_callbacks:
            self._drive_change_callbacks.remove(callback)
    
    def _is_cache_valid(self) -> bool:
        """Verifica se o cache ainda é válido."""
        if not self._cache_timestamp:
            return False
        
        elapsed = time.time() - self._cache_timestamp
        return elapsed < self._cache_duration
    
    def _refresh_drives_cache(self) -> None:
        """Atualiza o cache de drives detectados."""
        try:
            new_drives = {}
            
            # Obter partições do sistema
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    # Extrair letra do drive (Windows)
                    if platform.system() == "Windows":
                        drive_letter = partition.mountpoint.rstrip("\\")
                        if not drive_letter.endswith(":"):
                            continue
                    else:
                        drive_letter = partition.mountpoint
                    
                    # Obter informações de uso
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        total_space = usage.total
                        free_space = usage.free
                        used_space = usage.used
                    except (PermissionError, OSError):
                        # Drive não acessível
                        total_space = free_space = used_space = 0
                    
                    # Determinar tipo do drive
                    drive_type = self._determine_drive_type(partition)
                    
                    # Verificar se o drive está pronto
                    is_ready = self._is_drive_ready(partition.mountpoint)
                    
                    # Criar objeto DriveInfo
                    drive_info = DriveInfo(
                        letter=drive_letter,
                        label=self._get_drive_label(partition.mountpoint),
                        file_system=partition.fstype,
                        total_space=total_space,
                        free_space=free_space,
                        used_space=used_space,
                        drive_type=drive_type,
                        is_ready=is_ready,
                        mount_point=partition.mountpoint,
                        device=partition.device
                    )
                    
                    new_drives[drive_letter] = drive_info
                    
                except Exception as e:
                    self.logger.warning(f"Erro ao processar partição {partition.mountpoint}: {e}")
                    continue
            
            # Detectar mudanças e notificar callbacks
            if self._drives_cache != new_drives:
                self._notify_drive_changes(self._drives_cache, new_drives)
            
            self._drives_cache = new_drives
            self._cache_timestamp = time.time()
            
            self.logger.debug(f"Cache de drives atualizado: {len(new_drives)} drives detectados")
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar cache de drives: {e}")
    
    def _determine_drive_type(self, partition) -> str:
        """Determina o tipo do drive baseado nas informações da partição."""
        try:
            # No Windows, usar informações do sistema
            if platform.system() == "Windows":
                try:
                    import win32file
                    drive_type_map = {
                        win32file.DRIVE_FIXED: "fixed",
                        win32file.DRIVE_REMOVABLE: "removable",
                        win32file.DRIVE_REMOTE: "network",
                        win32file.DRIVE_CDROM: "cdrom",
                        win32file.DRIVE_RAMDISK: "ramdisk"
                    }
                    
                    drive_type = win32file.GetDriveType(partition.mountpoint)
                    return drive_type_map.get(drive_type, "unknown")
                except ImportError:
                    # win32file não disponível, usar fallback
                    pass
            
            # Fallback baseado no tipo de sistema de arquivos
            if partition.fstype in ["NTFS", "exFAT"]:
                return "fixed"
            elif partition.fstype in ["FAT32", "FAT"]:
                return "removable"
            else:
                return "unknown"
                
        except Exception:
            return "unknown"
    
    def _is_drive_ready(self, mountpoint: str) -> bool:
        """Verifica se o drive está pronto para uso."""
        try:
            # Tentar acessar o diretório
            Path(mountpoint).exists()
            return True
        except (PermissionError, OSError):
            return False
    
    def _get_drive_label(self, mountpoint: str) -> str:
        """Obtém o rótulo do drive."""
        try:
            if platform.system() == "Windows":
                try:
                    import win32api
                    return win32api.GetVolumeInformation(mountpoint)[0] or ""
                except ImportError:
                    # win32api não disponível
                    pass
        except Exception:
            pass
        
        return ""
    
    def _notify_drive_changes(self, old_drives: Dict[str, DriveInfo], 
                            new_drives: Dict[str, DriveInfo]) -> None:
        """Notifica callbacks sobre mudanças nos drives."""
        try:
            changes = {
                'added': [],
                'removed': [],
                'modified': []
            }
            
            # Drives adicionados
            for letter, drive_info in new_drives.items():
                if letter not in old_drives:
                    changes['added'].append(drive_info)
            
            # Drives removidos
            for letter, drive_info in old_drives.items():
                if letter not in new_drives:
                    changes['removed'].append(drive_info)
            
            # Drives modificados
            for letter, new_drive in new_drives.items():
                if letter in old_drives:
                    old_drive = old_drives[letter]
                    if (old_drive.free_space != new_drive.free_space or
                        old_drive.is_ready != new_drive.is_ready):
                        changes['modified'].append(new_drive)
            
            # Notificar callbacks se houver mudanças
            if any(changes.values()):
                for callback in self._drive_change_callbacks:
                    try:
                        callback(changes)
                    except Exception as e:
                        self.logger.error(f"Erro ao notificar callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Erro ao notificar mudanças de drives: {e}")