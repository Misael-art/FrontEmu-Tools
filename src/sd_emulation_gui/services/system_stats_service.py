"""
System Statistics Service

Serviço responsável pela coleta e monitoramento de estatísticas do sistema,
incluindo métricas de performance, uso de recursos e monitoramento em tempo real.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from collections import deque

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
except ImportError as e:
    logging.warning(f"Failed to import utilities: {e}")
    
    class BaseService:
        def __init__(self):
            self.logger = logging.getLogger(self.__class__.__name__)
    
    class SystemUtils:
        @staticmethod
        def get_system_info():
            return {}
        
        @staticmethod
        def get_performance_metrics():
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


class SystemMetrics:
    """Classe para armazenar métricas do sistema em um ponto no tempo."""
    
    def __init__(self, timestamp: datetime = None):
        """Inicializa métricas do sistema.
        
        Args:
            timestamp: Timestamp das métricas (padrão: agora)
        """
        self.timestamp = timestamp or datetime.now()
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.memory_total = 0
        self.memory_available = 0
        self.disk_usage = {}  # Por drive
        self.network_io = {'bytes_sent': 0, 'bytes_recv': 0}
        self.process_count = 0
        self.uptime_seconds = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': round(self.cpu_usage, 2),
            'memory_usage': round(self.memory_usage, 2),
            'memory_total': self.memory_total,
            'memory_available': self.memory_available,
            'memory_total_gb': round(self.memory_total / (1024**3), 2),
            'memory_available_gb': round(self.memory_available / (1024**3), 2),
            'disk_usage': self.disk_usage,
            'network_io': self.network_io,
            'process_count': self.process_count,
            'uptime_seconds': self.uptime_seconds,
            'uptime_formatted': self._format_uptime(self.uptime_seconds)
        }
    
    def _format_uptime(self, seconds: int) -> str:
        """Formata tempo de atividade em formato legível."""
        try:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "unknown"


class SystemStatsService(BaseService):
    """Serviço para coleta e monitoramento de estatísticas do sistema."""
    
    def __init__(self, base_path: str = None):
        """Inicializa o serviço de estatísticas do sistema.
        
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
        
        # Configurações de monitoramento
        self.monitoring_enabled = False
        self.monitoring_interval = 5  # Segundos entre coletas
        self.history_size = 720  # Manter 1 hora de histórico (720 * 5s = 3600s)
        
        # Histórico de métricas
        self.metrics_history = deque(maxlen=self.history_size)
        self.current_metrics = None
        
        # Threading para monitoramento
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Callbacks para alertas
        self._alert_callbacks = []
        
        # Thresholds para alertas
        self.cpu_alert_threshold = 80.0  # CPU > 80%
        self.memory_alert_threshold = 85.0  # Memória > 85%
        self.disk_alert_threshold = 90.0  # Disco > 90%
        
        # Cache para informações do sistema
        self._system_info_cache = None
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutos
    
    def initialize(self) -> None:
        """Inicializa o SystemStatsService."""
        try:
            self.logger.info("Inicializando SystemStatsService...")
            
            # Garantir que os atributos existam
            if not hasattr(self, 'metrics_history'):
                self.metrics_history = deque(maxlen=720)
            if not hasattr(self, 'current_metrics'):
                self.current_metrics = None
            if not hasattr(self, '_alert_callbacks'):
                self._alert_callbacks = []
            if not hasattr(self, '_system_info_cache'):
                self._system_info_cache = None
            if not hasattr(self, '_cache_timestamp'):
                self._cache_timestamp = None
            
            # Coletar métricas iniciais (sem falhar se houver erro)
            try:
                self.current_metrics = self._collect_current_metrics()
                
                # Adicionar ao histórico
                if self.current_metrics:
                    self.metrics_history.append(self.current_metrics)
            except Exception as metrics_error:
                self.logger.warning(f"Erro ao coletar métricas iniciais: {metrics_error}")
            
            self.logger.info("SystemStatsService inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar SystemStatsService: {e}")
            # Não fazer raise para permitir que o container continue funcionando
            # Definir valores padrão em caso de erro
            if not hasattr(self, 'metrics_history'):
                self.metrics_history = deque(maxlen=720)
            if not hasattr(self, 'current_metrics'):
                self.current_metrics = None
            if not hasattr(self, '_alert_callbacks'):
                self._alert_callbacks = []
            if not hasattr(self, '_system_info_cache'):
                self._system_info_cache = None
            if not hasattr(self, '_cache_timestamp'):
                self._cache_timestamp = None
    
    def _is_cache_valid(self) -> bool:
        """Verifica se o cache de informações do sistema é válido."""
        if not self._cache_timestamp:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration
    
    def _collect_current_metrics(self) -> SystemMetrics:
        """Coleta métricas atuais do sistema."""
        try:
            metrics = SystemMetrics()
            
            # Obter métricas de performance
            performance_data = SystemUtils.get_system_performance()
            
            # CPU
            metrics.cpu_usage = performance_data.get('cpu_percent', 0.0)
            
            # Memória
            memory_data = performance_data.get('memory', {})
            metrics.memory_total = memory_data.get('total', 0)
            metrics.memory_available = memory_data.get('available', 0)
            if metrics.memory_total > 0:
                used_memory = metrics.memory_total - metrics.memory_available
                metrics.memory_usage = (used_memory / metrics.memory_total) * 100
            
            # Disco
            disk_data = performance_data.get('disk_usage', {})
            for drive, usage_info in disk_data.items():
                if isinstance(usage_info, dict):
                    metrics.disk_usage[drive] = {
                        'usage_percent': usage_info.get('usage_percent', 0),
                        'free_gb': round(usage_info.get('free', 0) / (1024**3), 2),
                        'total_gb': round(usage_info.get('total', 0) / (1024**3), 2)
                    }
            
            # Rede
            network_data = performance_data.get('network_io', {})
            metrics.network_io = {
                'bytes_sent': network_data.get('bytes_sent', 0),
                'bytes_recv': network_data.get('bytes_recv', 0)
            }
            
            # Processos
            metrics.process_count = performance_data.get('process_count', 0)
            
            # Uptime
            metrics.uptime_seconds = performance_data.get('uptime_seconds', 0)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Erro ao coletar métricas do sistema: {e}")
            return SystemMetrics()  # Retorna métricas vazias em caso de erro
    
    def get_current_metrics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtém métricas atuais do sistema.
        
        Args:
            force_refresh: Força coleta de novas métricas
            
        Returns:
            Dicionário com métricas atuais
        """
        try:
            if force_refresh or not self.current_metrics:
                self.current_metrics = self._collect_current_metrics()
                
                # Adicionar ao histórico se não estiver monitorando
                if not self.monitoring_enabled:
                    self.metrics_history.append(self.current_metrics)
            
            return self.current_metrics.to_dict() if self.current_metrics else {}
            
        except Exception as e:
            self.logger.error(f"Erro ao obter métricas atuais: {e}")
            return {}
    
    def get_system_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtém informações gerais do sistema.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            Dicionário com informações do sistema
        """
        try:
            if force_refresh or not self._is_cache_valid():
                self._system_info_cache = SystemUtils.get_system_info()
                self._cache_timestamp = datetime.now()
            
            return self._system_info_cache.copy() if self._system_info_cache else {}
            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do sistema: {e}")
            return {}
    
    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Obtém histórico de métricas.
        
        Args:
            minutes: Número de minutos de histórico para retornar
            
        Returns:
            Lista com histórico de métricas
        """
        try:
            # Calcular quantos pontos de dados representam o período solicitado
            points_needed = (minutes * 60) // self.monitoring_interval
            
            # Obter últimos pontos do histórico
            recent_metrics = list(self.metrics_history)[-points_needed:] if points_needed > 0 else list(self.metrics_history)
            
            return [metrics.to_dict() for metrics in recent_metrics]
            
        except Exception as e:
            self.logger.error(f"Erro ao obter histórico de métricas: {e}")
            return []
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Obtém resumo de performance do período especificado.
        
        Args:
            minutes: Período em minutos para análise
            
        Returns:
            Dicionário com resumo de performance
        """
        try:
            history = self.get_metrics_history(minutes)
            
            if not history:
                return {}
            
            # Calcular estatísticas
            cpu_values = [m['cpu_usage'] for m in history if 'cpu_usage' in m]
            memory_values = [m['memory_usage'] for m in history if 'memory_usage' in m]
            
            summary = {
                'period_minutes': minutes,
                'data_points': len(history),
                'timestamp_start': history[0]['timestamp'] if history else None,
                'timestamp_end': history[-1]['timestamp'] if history else None,
                'cpu': self._calculate_stats(cpu_values),
                'memory': self._calculate_stats(memory_values),
                'disk_usage': {},
                'alerts_triggered': self._count_alerts_in_period(history)
            }
            
            # Calcular estatísticas de disco por drive
            if history:
                # Obter todos os drives presentes no histórico
                all_drives = set()
                for metrics in history:
                    if 'disk_usage' in metrics:
                        all_drives.update(metrics['disk_usage'].keys())
                
                # Calcular estatísticas para cada drive
                for drive in all_drives:
                    drive_values = []
                    for metrics in history:
                        disk_data = metrics.get('disk_usage', {})
                        if drive in disk_data:
                            drive_values.append(disk_data[drive].get('usage_percent', 0))
                    
                    if drive_values:
                        summary['disk_usage'][drive] = self._calculate_stats(drive_values)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular resumo de performance: {e}")
            return {}
    
    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """Calcula estatísticas básicas para uma lista de valores."""
        if not values:
            return {'min': 0, 'max': 0, 'avg': 0, 'current': 0}
        
        return {
            'min': round(min(values), 2),
            'max': round(max(values), 2),
            'avg': round(sum(values) / len(values), 2),
            'current': round(values[-1], 2)
        }
    
    def _count_alerts_in_period(self, history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Conta alertas disparados no período."""
        alerts = {'cpu': 0, 'memory': 0, 'disk': 0}
        
        for metrics in history:
            # CPU alerts
            if metrics.get('cpu_usage', 0) > self.cpu_alert_threshold:
                alerts['cpu'] += 1
            
            # Memory alerts
            if metrics.get('memory_usage', 0) > self.memory_alert_threshold:
                alerts['memory'] += 1
            
            # Disk alerts
            disk_usage = metrics.get('disk_usage', {})
            for drive, usage_info in disk_usage.items():
                if isinstance(usage_info, dict) and usage_info.get('usage_percent', 0) > self.disk_alert_threshold:
                    alerts['disk'] += 1
                    break  # Contar apenas uma vez por coleta
        
        return alerts
    
    def start_monitoring(self, interval_seconds: int = None) -> None:
        """Inicia monitoramento contínuo do sistema.
        
        Args:
            interval_seconds: Intervalo entre coletas (padrão: 5 segundos)
        """
        try:
            if self.monitoring_enabled:
                self.logger.warning("Monitoramento já está ativo")
                return
            
            if interval_seconds:
                self.monitoring_interval = interval_seconds
            
            self.monitoring_enabled = True
            self._stop_monitoring.clear()
            
            # Iniciar thread de monitoramento
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="SystemStatsMonitoring"
            )
            self._monitoring_thread.start()
            
            self.logger.info(f"Monitoramento iniciado (intervalo: {self.monitoring_interval}s)")
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar monitoramento: {e}")
            self.monitoring_enabled = False
    
    def stop_monitoring(self) -> None:
        """Para o monitoramento contínuo do sistema."""
        try:
            if not self.monitoring_enabled:
                self.logger.warning("Monitoramento não está ativo")
                return
            
            self.monitoring_enabled = False
            self._stop_monitoring.set()
            
            # Aguardar thread terminar
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10)
            
            self.logger.info("Monitoramento parado")
            
        except Exception as e:
            self.logger.error(f"Erro ao parar monitoramento: {e}")
    
    def _monitoring_loop(self) -> None:
        """Loop principal de monitoramento."""
        try:
            self.logger.debug("Loop de monitoramento iniciado")
            
            while not self._stop_monitoring.is_set():
                try:
                    # Coletar métricas
                    metrics = self._collect_current_metrics()
                    self.current_metrics = metrics
                    
                    # Adicionar ao histórico
                    self.metrics_history.append(metrics)
                    
                    # Verificar alertas
                    self._check_alerts(metrics)
                    
                    # Aguardar próximo ciclo
                    if self._stop_monitoring.wait(self.monitoring_interval):
                        break  # Stop event foi setado
                        
                except Exception as e:
                    self.logger.error(f"Erro no loop de monitoramento: {e}")
                    time.sleep(self.monitoring_interval)
            
            self.logger.debug("Loop de monitoramento finalizado")
            
        except Exception as e:
            self.logger.error(f"Erro fatal no loop de monitoramento: {e}")
        finally:
            self.monitoring_enabled = False
    
    def _check_alerts(self, metrics: SystemMetrics) -> None:
        """Verifica se algum threshold foi ultrapassado e dispara alertas."""
        try:
            alerts = []
            
            # CPU alert
            if metrics.cpu_usage > self.cpu_alert_threshold:
                alerts.append({
                    'type': 'cpu',
                    'severity': 'warning' if metrics.cpu_usage < 95 else 'critical',
                    'message': f'Alto uso de CPU: {metrics.cpu_usage:.1f}%',
                    'value': metrics.cpu_usage,
                    'threshold': self.cpu_alert_threshold
                })
            
            # Memory alert
            if metrics.memory_usage > self.memory_alert_threshold:
                alerts.append({
                    'type': 'memory',
                    'severity': 'warning' if metrics.memory_usage < 95 else 'critical',
                    'message': f'Alto uso de memória: {metrics.memory_usage:.1f}%',
                    'value': metrics.memory_usage,
                    'threshold': self.memory_alert_threshold
                })
            
            # Disk alerts
            for drive, usage_info in metrics.disk_usage.items():
                if isinstance(usage_info, dict):
                    usage_percent = usage_info.get('usage_percent', 0)
                    if usage_percent > self.disk_alert_threshold:
                        alerts.append({
                            'type': 'disk',
                            'severity': 'warning' if usage_percent < 98 else 'critical',
                            'message': f'Alto uso do disco {drive}: {usage_percent:.1f}%',
                            'value': usage_percent,
                            'threshold': self.disk_alert_threshold,
                            'drive': drive
                        })
            
            # Disparar callbacks de alerta
            if alerts:
                for callback in self._alert_callbacks:
                    try:
                        callback(alerts)
                    except Exception as e:
                        self.logger.error(f"Erro ao executar callback de alerta: {e}")
                        
        except Exception as e:
            self.logger.error(f"Erro ao verificar alertas: {e}")
    
    def add_alert_callback(self, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Adiciona callback para receber alertas.
        
        Args:
            callback: Função que será chamada quando alertas forem disparados
        """
        if callback not in self._alert_callbacks:
            self._alert_callbacks.append(callback)
            self.logger.debug("Callback de alerta adicionado")
    
    def remove_alert_callback(self, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Remove callback de alertas.
        
        Args:
            callback: Função a ser removida
        """
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            self.logger.debug("Callback de alerta removido")
    
    def set_alert_thresholds(self, cpu_threshold: float = None, 
                           memory_threshold: float = None, 
                           disk_threshold: float = None) -> None:
        """Define thresholds para alertas.
        
        Args:
            cpu_threshold: Threshold para CPU (%)
            memory_threshold: Threshold para memória (%)
            disk_threshold: Threshold para disco (%)
        """
        if cpu_threshold is not None:
            self.cpu_alert_threshold = cpu_threshold
        
        if memory_threshold is not None:
            self.memory_alert_threshold = memory_threshold
        
        if disk_threshold is not None:
            self.disk_alert_threshold = disk_threshold
        
        self.logger.info(f"Thresholds atualizados - CPU: {self.cpu_alert_threshold}%, "
                        f"Memória: {self.memory_alert_threshold}%, "
                        f"Disco: {self.disk_alert_threshold}%")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Obtém status geral de saúde do sistema.
        
        Returns:
            Dicionário com status de saúde
        """
        try:
            current = self.get_current_metrics()
            
            if not current:
                return {'status': 'unknown', 'message': 'Não foi possível obter métricas'}
            
            # Determinar status geral
            issues = []
            warnings = []
            
            # Verificar CPU
            cpu_usage = current.get('cpu_usage', 0)
            if cpu_usage > 95:
                issues.append(f'CPU crítica: {cpu_usage:.1f}%')
            elif cpu_usage > self.cpu_alert_threshold:
                warnings.append(f'CPU alta: {cpu_usage:.1f}%')
            
            # Verificar memória
            memory_usage = current.get('memory_usage', 0)
            if memory_usage > 95:
                issues.append(f'Memória crítica: {memory_usage:.1f}%')
            elif memory_usage > self.memory_alert_threshold:
                warnings.append(f'Memória alta: {memory_usage:.1f}%')
            
            # Verificar discos
            disk_usage = current.get('disk_usage', {})
            for drive, usage_info in disk_usage.items():
                if isinstance(usage_info, dict):
                    usage_percent = usage_info.get('usage_percent', 0)
                    if usage_percent > 98:
                        issues.append(f'Disco {drive} crítico: {usage_percent:.1f}%')
                    elif usage_percent > self.disk_alert_threshold:
                        warnings.append(f'Disco {drive} alto: {usage_percent:.1f}%')
            
            # Determinar status final
            if issues:
                status = 'critical'
                message = f'{len(issues)} problema(s) crítico(s) detectado(s)'
            elif warnings:
                status = 'warning'
                message = f'{len(warnings)} aviso(s) detectado(s)'
            else:
                status = 'healthy'
                message = 'Sistema funcionando normalmente'
            
            return {
                'status': status,
                'message': message,
                'issues': issues,
                'warnings': warnings,
                'metrics': current,
                'monitoring_active': self.monitoring_enabled,
                'last_update': current.get('timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter status de saúde: {e}")
            return {
                'status': 'error',
                'message': f'Erro ao verificar saúde do sistema: {str(e)}'
            }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Verifica alertas baseados nas métricas atuais.
        
        Returns:
            Lista de alertas ativos
        """
        try:
            current_metrics = self.get_current_metrics()
            if not current_metrics:
                return []
            
            alerts = []
            
            # CPU alert
            cpu_usage = current_metrics.get('cpu_usage', 0)
            if cpu_usage > self.cpu_alert_threshold:
                alerts.append({
                    'type': 'cpu',
                    'severity': 'warning' if cpu_usage < 95 else 'critical',
                    'message': f'Alto uso de CPU: {cpu_usage:.1f}%',
                    'value': cpu_usage,
                    'threshold': self.cpu_alert_threshold
                })
            
            # Memory alert
            memory_usage = current_metrics.get('memory_usage', 0)
            if memory_usage > self.memory_alert_threshold:
                alerts.append({
                    'type': 'memory',
                    'severity': 'warning' if memory_usage < 95 else 'critical',
                    'message': f'Alto uso de memória: {memory_usage:.1f}%',
                    'value': memory_usage,
                    'threshold': self.memory_alert_threshold
                })
            
            # Disk alerts
            disk_usage = current_metrics.get('disk_usage', {})
            for drive, usage_info in disk_usage.items():
                if isinstance(usage_info, dict):
                    usage_percent = usage_info.get('usage_percent', 0)
                    if usage_percent > self.disk_alert_threshold:
                        alerts.append({
                            'type': 'disk',
                            'severity': 'warning' if usage_percent < 98 else 'critical',
                            'message': f'Alto uso do disco {drive}: {usage_percent:.1f}%',
                            'value': usage_percent,
                            'threshold': self.disk_alert_threshold,
                            'drive': drive
                        })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar alertas: {e}")
            return []