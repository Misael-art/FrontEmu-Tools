"""
Drive Manager Service

Serviço responsável pela identificação do drive padrão, gerenciamento de drives
alternativos e validação de drives para operações do sistema.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

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
        
        @staticmethod
        def get_drive_info(drive):
            return {}
    
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


class DriveManagerService(BaseService):
    """Serviço para gerenciamento de drives do sistema."""
    
    def __init__(self, base_path: str = None):
        """Inicializa o serviço de gerenciamento de drives.
        
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
        
        # Cache para drives
        self._drives_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 60  # Cache válido por 60 segundos
        
        # Configurações de drives
        self._default_drive = None
        self._preferred_drives = []  # Lista de drives preferidos pelo usuário
        self._excluded_drives = set()  # Drives excluídos (removíveis, rede, etc.)
        
        # Critérios de validação
        self.min_space_gb = 10  # Espaço mínimo para considerar um drive válido
        self.max_usage_percentage = 90  # Uso máximo para considerar um drive válido
        
        # Auto-inicializar o serviço
        try:
            self.initialize()
        except Exception as e:
            self.logger.warning(f"Falha na auto-inicialização: {e}")
        
    def initialize(self) -> None:
        """Inicializa o DriveManagerService."""
        try:
            self.logger.info("Inicializando DriveManagerService...")
            
            # Garantir que os atributos existam
            if not hasattr(self, '_drives_cache'):
                self._drives_cache = {}
            if not hasattr(self, '_default_drive'):
                self._default_drive = None
            if not hasattr(self, '_excluded_drives'):
                self._excluded_drives = set()
            if not hasattr(self, '_cache_timestamp'):
                self._cache_timestamp = None
            
            # Atualizar cache de drives
            self._refresh_drives_cache()
            
            # Identificar drive padrão
            self._identify_default_drive()
            
            # Configurar drives excluídos
            self._configure_excluded_drives()
            
            self.logger.info(f"DriveManagerService inicializado. Drive padrão: {self._default_drive}")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar DriveManagerService: {e}")
            # Não fazer raise para permitir que o container continue funcionando
            # Definir valores padrão em caso de erro
            if not hasattr(self, '_drives_cache'):
                self._drives_cache = {}
            if not hasattr(self, '_default_drive'):
                self._default_drive = 'C:'  # Fallback para Windows
            if not hasattr(self, '_excluded_drives'):
                self._excluded_drives = set()
            # Garantir que os atributos de configuração existam
            if not hasattr(self, 'min_space_gb'):
                self.min_space_gb = 10
            if not hasattr(self, 'max_usage_percentage'):
                self.max_usage_percentage = 90
    
    def _is_cache_valid(self) -> bool:
        """Verifica se o cache de drives ainda é válido."""
        if not self._cache_timestamp:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration
    
    def _refresh_drives_cache(self) -> None:
        """Atualiza o cache de informações dos drives."""
        try:
            self._drives_cache.clear()
            
            # Obter todos os drives do sistema
            drives = DriveUtils.get_all_drives()
            
            for drive_info in drives:
                if not drive_info or not drive_info.letter:
                    continue
                
                # Converter DriveInfo para dicionário
                drive_dict = {
                    'drive': drive_info.letter,
                    'letter': drive_info.letter,
                    'label': drive_info.label,
                    'file_system': drive_info.file_system,
                    'total_space': drive_info.total_space,
                    'free_space': drive_info.free_space,
                    'used_space': drive_info.used_space,
                    'usage_percentage': drive_info.usage_percentage,
                    'is_ready': drive_info.is_ready,
                    'drive_type': drive_info.drive_type,
                    'total_gb': drive_info.total_space / (1024**3) if drive_info.total_space else 0,
                    'free_gb': drive_info.free_space / (1024**3) if drive_info.free_space else 0,
                    'used_gb': drive_info.used_space / (1024**3) if drive_info.used_space else 0
                }
                
                # Adicionar status de saúde
                health_info = DriveUtils.get_drive_health_status(drive_info.letter)
                drive_dict['health_status'] = health_info.get('status', 'unknown')
                
                self._drives_cache[drive_info.letter] = drive_dict
            
            self._cache_timestamp = datetime.now()
            self.logger.debug(f"Cache de drives atualizado: {len(self._drives_cache)} drives encontrados")
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar cache de drives: {e}")
    
    def _identify_default_drive(self) -> None:
        """Identifica o drive padrão do sistema."""
        try:
            # Verificar se já foi identificado
            if self._default_drive:
                return
            
            # Estratégia 1: Drive C: no Windows
            system_info = SystemUtils.get_system_info()
            if system_info.get('os', '').lower().startswith('windows'):
                if 'C:' in self._drives_cache:
                    drive_info = self._drives_cache['C:']
                    if drive_info['drive_type'] == 'fixed':
                        self._default_drive = 'C:'
                        self.logger.info("Drive padrão identificado: C: (Windows)")
                        return
            
            # Estratégia 2: Primeiro drive fixo com maior espaço
            fixed_drives = [
                (drive, info) for drive, info in self._drives_cache.items()
                if info['drive_type'] == 'fixed'
            ]
            
            if fixed_drives:
                # Ordenar por espaço total (maior primeiro)
                fixed_drives.sort(key=lambda x: x[1]['total_space'], reverse=True)
                self._default_drive = fixed_drives[0][0]
                self.logger.info(f"Drive padrão identificado: {self._default_drive} (maior drive fixo)")
                return
            
            # Estratégia 3: Primeiro drive disponível
            if self._drives_cache:
                self._default_drive = list(self._drives_cache.keys())[0]
                self.logger.warning(f"Drive padrão identificado: {self._default_drive} (fallback)")
            else:
                self.logger.error("Nenhum drive encontrado no sistema")
                
        except Exception as e:
            self.logger.error(f"Erro ao identificar drive padrão: {e}")
    
    def _configure_excluded_drives(self) -> None:
        """Configura drives que devem ser excluídos das operações."""
        try:
            # Garantir que os atributos necessários existam
            if not hasattr(self, 'min_space_gb'):
                self.min_space_gb = 10
            if not hasattr(self, 'max_usage_percentage'):
                self.max_usage_percentage = 90
                
            self._excluded_drives.clear()
            
            for drive_letter, drive_info in self._drives_cache.items():
                drive_type = drive_info['drive_type']
                
                # Excluir drives removíveis e de rede por padrão
                if drive_type in ['removable', 'network', 'cdrom']:
                    self._excluded_drives.add(drive_letter)
                    self.logger.debug(f"Drive {drive_letter} excluído (tipo: {drive_type})")
                
                # Excluir drives com pouco espaço
                total_space_gb = drive_info['total_space'] / (1024**3)
                if total_space_gb < self.min_space_gb:
                    self._excluded_drives.add(drive_letter)
                    self.logger.debug(f"Drive {drive_letter} excluído (pouco espaço: {total_space_gb:.1f}GB)")
            
            self.logger.info(f"Drives excluídos: {list(self._excluded_drives)}")
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar drives excluídos: {e}")
    
    def get_default_drive(self, force_refresh: bool = False) -> Optional[str]:
        """Obtém o drive padrão do sistema.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            Letra do drive padrão ou None se não encontrado
        """
        if force_refresh or not self._is_cache_valid():
            self._refresh_drives_cache()
            self._identify_default_drive()
        
        return self._default_drive
    
    def get_default_drive_info(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Obtém informações detalhadas do drive padrão.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            Dicionário com informações do drive padrão ou None se não encontrado
        """
        default_drive = self.get_default_drive(force_refresh)
        if not default_drive:
            return None
        
        if force_refresh or not self._is_cache_valid():
            self._refresh_drives_cache()
        
        drive_info = self._drives_cache.get(default_drive)
        if drive_info:
            return {
                'drive': default_drive,
                'type': drive_info.get('drive_type', 'unknown'),
                'label': drive_info.get('label', ''),
                'file_system': drive_info.get('file_system', ''),
                'total_space': drive_info.get('total_space', 0),
                'free_space': drive_info.get('free_space', 0),
                'used_space': drive_info.get('used_space', 0),
                'usage_percentage': drive_info.get('usage_percentage', 0),
                'health_status': drive_info.get('health_status', 'unknown'),
                'total_gb': drive_info.get('total_gb', 0),
                'free_gb': drive_info.get('free_gb', 0),
                'used_gb': drive_info.get('used_gb', 0)
            }
        
        return None
    
    def get_available_drives(self, force_refresh: bool = False, 
                           include_excluded: bool = False) -> Dict[str, Dict[str, Any]]:
        """Obtém lista de drives disponíveis para uso.
        
        Args:
            force_refresh: Força atualização do cache
            include_excluded: Inclui drives excluídos na lista
            
        Returns:
            Dicionário com drives disponíveis
        """
        if force_refresh or not self._is_cache_valid():
            self._refresh_drives_cache()
            self._configure_excluded_drives()
        
        available_drives = {}
        
        for drive_letter, drive_info in self._drives_cache.items():
            # Verificar se deve incluir drives excluídos
            if not include_excluded and drive_letter in self._excluded_drives:
                continue
            
            # Adicionar informações extras
            enhanced_info = drive_info.copy()
            enhanced_info['is_default'] = drive_letter == self._default_drive
            enhanced_info['is_excluded'] = drive_letter in self._excluded_drives
            enhanced_info['is_preferred'] = drive_letter in self._preferred_drives
            enhanced_info['suitability_score'] = self._calculate_suitability_score(drive_info)
            
            available_drives[drive_letter] = enhanced_info
        
        return available_drives
    
    def _calculate_suitability_score(self, drive_info: Dict[str, Any]) -> float:
        """Calcula pontuação de adequação de um drive.
        
        Args:
            drive_info: Informações do drive
            
        Returns:
            Pontuação de 0 a 100 (maior = melhor)
        """
        score = 0.0
        
        try:
            # Pontuação base por tipo de drive
            drive_type = drive_info['drive_type']
            if drive_type == 'fixed':
                score += 40
            elif drive_type == 'unknown':
                score += 20
            else:
                score += 10
            
            # Pontuação por espaço livre
            free_space_gb = drive_info['free_space'] / (1024**3)
            if free_space_gb >= 100:
                score += 30
            elif free_space_gb >= 50:
                score += 20
            elif free_space_gb >= 20:
                score += 10
            elif free_space_gb >= 10:
                score += 5
            
            # Penalização por uso alto
            usage_percentage = drive_info['usage_percentage']
            if usage_percentage < 50:
                score += 20
            elif usage_percentage < 70:
                score += 10
            elif usage_percentage < 85:
                score += 5
            else:
                score -= 10
            
            # Bonificação por saúde do drive
            health_status = drive_info.get('health_status', 'unknown')
            if health_status == 'healthy':
                score += 10
            elif health_status == 'warning':
                score -= 5
            elif health_status == 'critical':
                score -= 20
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular pontuação de adequação: {e}")
        
        return max(0, min(100, score))
    
    def get_recommended_drives(self, required_space_gb: float = 0, 
                             max_results: int = 5) -> List[Dict[str, Any]]:
        """Obtém lista de drives recomendados ordenados por adequação.
        
        Args:
            required_space_gb: Espaço mínimo necessário em GB
            max_results: Número máximo de resultados
            
        Returns:
            Lista de drives recomendados ordenados por pontuação
        """
        available_drives = self.get_available_drives()
        recommended = []
        
        for drive_letter, drive_info in available_drives.items():
            # Verificar espaço mínimo
            free_space_gb = drive_info.get('free_space', 0) / (1024**3)
            if required_space_gb > 0 and free_space_gb < required_space_gb:
                continue
            
            # Verificar uso máximo
            usage_percentage = drive_info.get('usage_percentage', 100)
            if usage_percentage > self.max_usage_percentage:
                continue
            
            recommended.append({
                'drive': drive_letter,
                'info': drive_info,
                'score': drive_info.get('suitability_score', 0),
                'free_space_gb': round(free_space_gb, 2),
                'usage_percentage': round(usage_percentage, 2)
            })
        
        # Ordenar por pontuação (maior primeiro)
        recommended.sort(key=lambda x: x['score'], reverse=True)
        
        return recommended[:max_results]
    
    def validate_drive_selection(self, drive_letter: str, 
                                required_space_gb: float = 0) -> Dict[str, Any]:
        """Valida a seleção de um drive específico.
        
        Args:
            drive_letter: Letra do drive para validar
            required_space_gb: Espaço mínimo necessário em GB
            
        Returns:
            Dicionário com resultado da validação
        """
        try:
            # Normalizar letra do drive
            drive_letter = drive_letter.upper()
            if not drive_letter.endswith(':'):
                drive_letter += ':'
            
            # Verificar se o drive existe
            if drive_letter not in self._drives_cache:
                return {
                    'valid': False,
                    'reason': f'Drive {drive_letter} não encontrado',
                    'drive': drive_letter,
                    'severity': 'error'
                }
            
            drive_info = self._drives_cache[drive_letter]
            issues = []
            warnings = []
            
            # Verificar tipo de drive
            drive_type = drive_info.get('drive_type', 'unknown')
            if drive_type in ['removable', 'network']:
                issues.append(f'Drive {drive_letter} é do tipo {drive_type} (não recomendado)')
            
            # Verificar espaço disponível
            free_space_gb = drive_info.get('free_space', 0) / (1024**3)
            if required_space_gb > 0 and free_space_gb < required_space_gb:
                issues.append(f'Espaço insuficiente. Necessário: {required_space_gb}GB, Disponível: {free_space_gb:.1f}GB')
            
            # Verificar uso do disco
            usage_percentage = drive_info.get('usage_percentage', 0)
            if usage_percentage > self.max_usage_percentage:
                issues.append(f'Uso muito alto do disco: {usage_percentage:.1f}%')
            elif usage_percentage > 80:
                warnings.append(f'Uso alto do disco: {usage_percentage:.1f}%')
            
            # Verificar saúde do drive
            health_status = drive_info.get('health_status', 'unknown')
            if health_status == 'critical':
                issues.append(f'Drive {drive_letter} com problemas críticos de saúde')
            elif health_status == 'warning':
                warnings.append(f'Drive {drive_letter} com avisos de saúde')
            
            # Verificar se está excluído
            if drive_letter in self._excluded_drives:
                warnings.append(f'Drive {drive_letter} está na lista de excluídos')
            
            # Determinar resultado
            if issues:
                return {
                    'valid': False,
                    'reason': '; '.join(issues),
                    'drive': drive_letter,
                    'drive_info': drive_info,
                    'issues': issues,
                    'warnings': warnings,
                    'severity': 'error'
                }
            
            return {
                'valid': True,
                'reason': 'Drive válido para uso',
                'drive': drive_letter,
                'drive_info': drive_info,
                'warnings': warnings,
                'suitability_score': self._calculate_suitability_score(drive_info),
                'severity': 'warning' if warnings else 'info'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao validar drive {drive_letter}: {e}")
            return {
                'valid': False,
                'reason': f'Erro ao validar drive: {str(e)}',
                'drive': drive_letter,
                'severity': 'error'
            }
    
    def set_preferred_drives(self, drive_letters: List[str]) -> None:
        """Define lista de drives preferidos pelo usuário.
        
        Args:
            drive_letters: Lista de letras de drives preferidos
        """
        try:
            self._preferred_drives = [
                drive.upper() + (':' if not drive.endswith(':') else '')
                for drive in drive_letters
            ]
            
            self.logger.info(f"Drives preferidos definidos: {self._preferred_drives}")
            
        except Exception as e:
            self.logger.error(f"Erro ao definir drives preferidos: {e}")
    
    def add_excluded_drive(self, drive_letter: str) -> None:
        """Adiciona um drive à lista de excluídos.
        
        Args:
            drive_letter: Letra do drive para excluir
        """
        try:
            drive_letter = drive_letter.upper()
            if not drive_letter.endswith(':'):
                drive_letter += ':'
            
            self._excluded_drives.add(drive_letter)
            self.logger.info(f"Drive {drive_letter} adicionado à lista de excluídos")
            
        except Exception as e:
            self.logger.error(f"Erro ao excluir drive {drive_letter}: {e}")
    
    def remove_excluded_drive(self, drive_letter: str) -> None:
        """Remove um drive da lista de excluídos.
        
        Args:
            drive_letter: Letra do drive para remover da exclusão
        """
        try:
            drive_letter = drive_letter.upper()
            if not drive_letter.endswith(':'):
                drive_letter += ':'
            
            self._excluded_drives.discard(drive_letter)
            self.logger.info(f"Drive {drive_letter} removido da lista de excluídos")
            
        except Exception as e:
            self.logger.error(f"Erro ao remover exclusão do drive {drive_letter}: {e}")
    
    def get_drive_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas gerais dos drives do sistema.
        
        Returns:
            Dicionário com estatísticas dos drives
        """
        try:
            if not self._is_cache_valid():
                self._refresh_drives_cache()
            
            stats = {
                'total_drives': len(self._drives_cache),
                'excluded_drives': len(self._excluded_drives),
                'available_drives': len(self._drives_cache) - len(self._excluded_drives),
                'default_drive': self._default_drive,
                'preferred_drives': len(self._preferred_drives),
                'drive_types': {},
                'total_space_gb': 0,
                'total_free_space_gb': 0,
                'total_used_space_gb': 0,
                'average_usage_percentage': 0
            }
            
            total_usage = 0
            
            for drive_letter, drive_info in self._drives_cache.items():
                # Contabilizar tipos de drive
                drive_type = drive_info.get('drive_type', 'unknown')
                stats['drive_types'][drive_type] = stats['drive_types'].get(drive_type, 0) + 1
                
                # Somar espaços
                total_space = drive_info.get('total_space', 0)
                free_space = drive_info.get('free_space', 0)
                used_space = drive_info.get('used_space', 0)
                
                stats['total_space_gb'] += total_space / (1024**3)
                stats['total_free_space_gb'] += free_space / (1024**3)
                stats['total_used_space_gb'] += used_space / (1024**3)
                
                # Somar uso percentual
                usage_percentage = drive_info.get('usage_percentage', 0)
                total_usage += usage_percentage
            
            # Calcular média de uso
            if self._drives_cache:
                stats['average_usage_percentage'] = total_usage / len(self._drives_cache)
            
            # Arredondar valores
            stats['total_space_gb'] = round(stats['total_space_gb'], 2)
            stats['total_free_space_gb'] = round(stats['total_free_space_gb'], 2)
            stats['total_used_space_gb'] = round(stats['total_used_space_gb'], 2)
            stats['average_usage_percentage'] = round(stats['average_usage_percentage'], 2)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas dos drives: {e}")
            return {}