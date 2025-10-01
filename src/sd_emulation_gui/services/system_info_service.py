"""
System Information Service

Serviço responsável por verificação de espaço em disco, informações de drives
e monitoramento de recursos do sistema para garantir operações seguras.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Import centralized systems
from sd_emulation_gui.app.imports_manager import configure_imports, import_with_fallback
from sd_emulation_gui.app.factory import FallbackFactory

# Configure imports centrally
configure_imports()

# Import with proper fallbacks
PathConfigManager = import_with_fallback(
    'path_config.PathConfigManager',
    FallbackFactory.create_service_fallback
)

PathResolver = import_with_fallback(
    'path_resolver.PathResolver',
    FallbackFactory.create_service_fallback
)

# Import utilities with simple fallbacks
try:
    from sd_emulation_gui.utils.base_service import BaseService
    from sd_emulation_gui.utils.system_utils import SystemUtils
    from sd_emulation_gui.utils.drive_utils import DriveUtils
    from sd_emulation_gui.utils.path_utils import PathUtils
    from sd_emulation_gui.utils.file_utils import FileUtils
except ImportError as e:
    logging.warning(f"Failed to import utilities: {e}")
    
    class BaseService:
        def __init__(self):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    class SystemUtils:
        @staticmethod
        def get_system_info():
            return {}
    
    class DriveUtils:
        @staticmethod
        def get_all_drives():
            return []
    
    class PathUtils:
        @staticmethod
        def normalize_path(path: str) -> str:
            import os
            return os.path.normpath(path)
    
    class FileUtils:
        @staticmethod
        def exists(path: str) -> bool:
            import os
            return os.path.exists(path)


class DriveInfo:
    """Informações detalhadas de um drive do sistema."""
    
    def __init__(self, drive_letter: str, label: str = "", file_system: str = "",
                 total_space: int = 0, free_space: int = 0, used_space: int = 0,
                 drive_type: str = "unknown", health_status: str = "unknown"):
        """Inicializa informações do drive.
        
        Args:
            drive_letter: Letra do drive (ex: 'C:', 'D:')
            label: Rótulo do drive
            file_system: Sistema de arquivos (NTFS, FAT32, etc.)
            total_space: Espaço total em bytes
            free_space: Espaço livre em bytes
            used_space: Espaço usado em bytes
            drive_type: Tipo do drive (fixed, removable, network, etc.)
            health_status: Status de saúde do drive
        """
        self.drive_letter = drive_letter
        self.label = label
        self.file_system = file_system
        self.total_space = total_space
        self.free_space = free_space
        self.used_space = used_space
        self.drive_type = drive_type
        self.health_status = health_status
        self.usage_percentage = (used_space / total_space * 100) if total_space > 0 else 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte informações do drive para dicionário."""
        return {
            'drive_letter': self.drive_letter,
            'label': self.label,
            'file_system': self.file_system,
            'total_space': self.total_space,
            'free_space': self.free_space,
            'used_space': self.used_space,
            'usage_percentage': round(self.usage_percentage, 2),
            'drive_type': self.drive_type,
            'health_status': self.health_status,
            'total_space_formatted': DriveUtils.format_bytes(self.total_space),
            'free_space_formatted': DriveUtils.format_bytes(self.free_space),
            'used_space_formatted': DriveUtils.format_bytes(self.used_space)
        }


class SystemInfoService(BaseService):
    """Serviço para informações do sistema e verificação de drives."""
    
    def __init__(self, base_path: str = None):
        """Inicializa o serviço de informações do sistema.
        
        Args:
            base_path: Caminho base para configurações (opcional)
        """
        super().__init__()
        
        # Initialize path management
        self.path_config_manager = PathConfigManager()
        self.path_resolver = PathResolver()
        
        if base_path:
            self.base_path = PathUtils.normalize_path(base_path)
        else:
            # Use dynamic path resolution
            try:
                resolved_path = self.path_resolver.resolve_path("config_base_path").resolved_path
                self.base_path = PathUtils.normalize_path(resolved_path)
            except Exception:
                self.base_path = "."
        
        # Cache para informações do sistema
        self._system_info_cache = {}
        self._drives_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 30  # Cache válido por 30 segundos
        
        # Configurações de alertas
        self.warning_threshold = 85  # Alerta quando uso > 85%
        self.critical_threshold = 95  # Crítico quando uso > 95%
        self.minimum_free_space_gb = 5  # Mínimo de 5GB livres
        
    def initialize(self) -> None:
        """Inicializa o SystemInfoService."""
        try:
            self.logger.info("Inicializando SystemInfoService...")
            
            # Verificar se utilitários estão disponíveis
            system_info = SystemUtils.get_system_info()
            self.logger.info(f"Sistema detectado: {system_info.get('os', 'Unknown')}")
            
            # Cache inicial das informações
            self._refresh_cache()
            
            self.logger.info("SystemInfoService inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar SystemInfoService: {e}")
            raise
    
    def _is_cache_valid(self) -> bool:
        """Verifica se o cache ainda é válido."""
        if not self._cache_timestamp:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration
    
    def _refresh_cache(self) -> None:
        """Atualiza o cache de informações do sistema."""
        try:
            self._system_info_cache = SystemUtils.get_system_info()
            self._drives_cache = self._get_drives_info()
            self._cache_timestamp = datetime.now()
            
            self.logger.debug("Cache de informações do sistema atualizado")
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar cache: {e}")
    
    def _get_drives_info(self) -> Dict[str, DriveInfo]:
        """Obtém informações detalhadas de todos os drives."""
        drives_info = {}
        
        try:
            drives = DriveUtils.get_all_drives()
            
            for drive_data in drives:
                # drive_data é um objeto DriveInfo, não um dicionário
                drive_letter = drive_data.letter
                if not drive_letter:
                    continue
                
                # Usar diretamente o objeto DriveInfo retornado
                drive_info = DriveInfo(
                    drive_letter=drive_letter,
                    label=drive_data.label or '',
                    file_system=drive_data.file_system or '',
                    total_space=drive_data.total_space or 0,
                    free_space=drive_data.free_space or 0,
                    used_space=drive_data.used_space or 0,
                    drive_type=drive_data.drive_type or 'unknown',
                    health_status=DriveUtils.get_drive_health_status(drive_letter)
                )
                
                drives_info[drive_letter] = drive_info
                
        except Exception as e:
            self.logger.error(f"Erro ao obter informações dos drives: {e}")
        
        return drives_info
    
    def get_system_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtém informações completas do sistema.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            Dicionário com informações do sistema
        """
        if force_refresh or not self._is_cache_valid():
            self._refresh_cache()
        
        return self._system_info_cache.copy()
    
    def get_all_drives_info(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Obtém informações de todos os drives do sistema.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            Dicionário com informações de todos os drives
        """
        if force_refresh or not self._is_cache_valid():
            self._refresh_cache()
        
        return {drive: info.to_dict() for drive, info in self._drives_cache.items()}
    
    def get_drive_info(self, drive_letter: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Obtém informações de um drive específico.
        
        Args:
            drive_letter: Letra do drive (ex: 'C:', 'D:')
            force_refresh: Força atualização do cache
            
        Returns:
            Dicionário com informações do drive ou None se não encontrado
        """
        if force_refresh or not self._is_cache_valid():
            self._refresh_cache()
        
        drive_info = self._drives_cache.get(drive_letter.upper())
        return drive_info.to_dict() if drive_info else None
    
    def check_disk_space(self, path: str, required_space_gb: float = 0) -> Dict[str, Any]:
        """Verifica espaço em disco para um caminho específico.
        
        Args:
            path: Caminho para verificar
            required_space_gb: Espaço necessário em GB (opcional)
            
        Returns:
            Dicionário com status da verificação
        """
        try:
            # Normalizar caminho e obter drive
            normalized_path = PathUtils.normalize_path(path)
            drive_letter = DriveUtils.get_drive_root(normalized_path)
            
            if not drive_letter:
                return {
                    'status': 'error',
                    'message': f'Não foi possível determinar o drive para: {path}',
                    'path': path,
                    'drive': None
                }
            
            # Obter informações do drive
            drive_info = self.get_drive_info(drive_letter)
            if not drive_info:
                return {
                    'status': 'error',
                    'message': f'Não foi possível obter informações do drive {drive_letter}',
                    'path': path,
                    'drive': drive_letter
                }
            
            # Verificar espaço disponível
            free_space_gb = drive_info['free_space'] / (1024**3)
            usage_percentage = drive_info['usage_percentage']
            
            # Determinar status
            status = 'ok'
            messages = []
            
            # Verificar se há espaço suficiente para operação
            if required_space_gb > 0 and free_space_gb < required_space_gb:
                status = 'insufficient_space'
                messages.append(f'Espaço insuficiente. Necessário: {required_space_gb:.1f}GB, Disponível: {free_space_gb:.1f}GB')
            
            # Verificar thresholds de uso
            if usage_percentage >= self.critical_threshold:
                status = 'critical' if status == 'ok' else status
                messages.append(f'Uso crítico do disco: {usage_percentage:.1f}%')
            elif usage_percentage >= self.warning_threshold:
                status = 'warning' if status == 'ok' else status
                messages.append(f'Uso alto do disco: {usage_percentage:.1f}%')
            
            # Verificar espaço mínimo livre
            if free_space_gb < self.minimum_free_space_gb:
                status = 'low_space' if status == 'ok' else status
                messages.append(f'Pouco espaço livre: {free_space_gb:.1f}GB (mínimo recomendado: {self.minimum_free_space_gb}GB)')
            
            return {
                'status': status,
                'messages': messages,
                'path': path,
                'drive': drive_letter,
                'drive_info': drive_info,
                'free_space_gb': round(free_space_gb, 2),
                'required_space_gb': required_space_gb,
                'sufficient_space': free_space_gb >= required_space_gb if required_space_gb > 0 else True,
                'usage_percentage': usage_percentage,
                'recommendations': self._get_space_recommendations(drive_info, required_space_gb)
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar espaço em disco para {path}: {e}")
            return {
                'status': 'error',
                'message': f'Erro ao verificar espaço em disco: {str(e)}',
                'path': path,
                'drive': None
            }
    
    def _get_space_recommendations(self, drive_info: Dict[str, Any], required_space_gb: float) -> List[str]:
        """Gera recomendações baseadas no espaço disponível.
        
        Args:
            drive_info: Informações do drive
            required_space_gb: Espaço necessário em GB
            
        Returns:
            Lista de recomendações
        """
        recommendations = []
        usage_percentage = drive_info['usage_percentage']
        free_space_gb = drive_info['free_space'] / (1024**3)
        
        if usage_percentage >= self.critical_threshold:
            recommendations.append("Libere espaço imediatamente - uso crítico do disco")
            recommendations.append("Execute limpeza de arquivos temporários")
            recommendations.append("Considere mover arquivos para outro drive")
        
        elif usage_percentage >= self.warning_threshold:
            recommendations.append("Considere liberar espaço em disco")
            recommendations.append("Monitore o uso do disco regularmente")
        
        if required_space_gb > 0 and free_space_gb < required_space_gb:
            needed_space = required_space_gb - free_space_gb
            recommendations.append(f"Libere pelo menos {needed_space:.1f}GB adicionais")
        
        if free_space_gb < self.minimum_free_space_gb:
            recommendations.append(f"Mantenha pelo menos {self.minimum_free_space_gb}GB livres para operação segura")
        
        return recommendations
    
    def get_default_drive(self) -> Optional[str]:
        """Identifica o drive padrão do sistema (geralmente C:).
        
        Returns:
            Letra do drive padrão ou None se não encontrado
        """
        try:
            # Primeiro, tentar obter o drive do sistema operacional
            system_info = self.get_system_info()
            if system_info.get('os', '').lower().startswith('windows'):
                # No Windows, C: é geralmente o drive padrão
                if 'C:' in self._drives_cache:
                    return 'C:'
            
            # Fallback: primeiro drive fixo encontrado
            for drive_letter, drive_info in self._drives_cache.items():
                if drive_info.drive_type == 'fixed':
                    return drive_letter
            
            # Último fallback: primeiro drive disponível
            if self._drives_cache:
                return list(self._drives_cache.keys())[0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao identificar drive padrão: {e}")
            return None
    
    def validate_drive_for_installation(self, drive_letter: str, required_space_gb: float = 10) -> Dict[str, Any]:
        """Valida se um drive é adequado para instalação.
        
        Args:
            drive_letter: Letra do drive para validar
            required_space_gb: Espaço mínimo necessário em GB
            
        Returns:
            Dicionário com resultado da validação
        """
        try:
            drive_info = self.get_drive_info(drive_letter)
            if not drive_info:
                return {
                    'valid': False,
                    'reason': f'Drive {drive_letter} não encontrado',
                    'drive': drive_letter
                }
            
            # Verificar se é um drive fixo
            if drive_info['drive_type'] not in ['fixed', 'unknown']:
                return {
                    'valid': False,
                    'reason': f'Drive {drive_letter} não é um drive fixo',
                    'drive': drive_letter,
                    'drive_info': drive_info
                }
            
            # Verificar espaço disponível
            free_space_gb = drive_info['free_space'] / (1024**3)
            if free_space_gb < required_space_gb:
                return {
                    'valid': False,
                    'reason': f'Espaço insuficiente. Necessário: {required_space_gb}GB, Disponível: {free_space_gb:.1f}GB',
                    'drive': drive_letter,
                    'drive_info': drive_info
                }
            
            # Verificar uso do disco
            if drive_info['usage_percentage'] >= self.critical_threshold:
                return {
                    'valid': False,
                    'reason': f'Uso crítico do disco: {drive_info["usage_percentage"]:.1f}%',
                    'drive': drive_letter,
                    'drive_info': drive_info
                }
            
            # Drive válido
            warnings = []
            if drive_info['usage_percentage'] >= self.warning_threshold:
                warnings.append(f'Uso alto do disco: {drive_info["usage_percentage"]:.1f}%')
            
            return {
                'valid': True,
                'reason': 'Drive adequado para instalação',
                'drive': drive_letter,
                'drive_info': drive_info,
                'warnings': warnings
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao validar drive {drive_letter}: {e}")
            return {
                'valid': False,
                'reason': f'Erro ao validar drive: {str(e)}',
                'drive': drive_letter
            }
    
    async def monitor_disk_space_async(self, paths: List[str], interval_seconds: int = 60) -> None:
        """Monitora espaço em disco de forma assíncrona.
        
        Args:
            paths: Lista de caminhos para monitorar
            interval_seconds: Intervalo entre verificações em segundos
        """
        self.logger.info(f"Iniciando monitoramento de espaço em disco para {len(paths)} caminhos")
        
        while True:
            try:
                for path in paths:
                    result = self.check_disk_space(path)
                    
                    if result['status'] in ['critical', 'low_space', 'insufficient_space']:
                        self.logger.warning(f"Alerta de espaço em disco para {path}: {result.get('messages', [])}")
                    elif result['status'] == 'warning':
                        self.logger.info(f"Aviso de espaço em disco para {path}: {result.get('messages', [])}")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Erro no monitoramento de espaço em disco: {e}")
                await asyncio.sleep(interval_seconds)