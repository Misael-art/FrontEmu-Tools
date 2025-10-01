"""
System Stats Service

Serviço responsável pelo monitoramento de estatísticas e performance do sistema,
seguindo os requisitos RF010 do DRS FrontEmu-Tools.
"""

import json
import logging
import psutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sd_emulation_gui.utils.base_service import BaseService


class SystemMetrics:
    """Métricas do sistema em um ponto no tempo."""
    
    def __init__(self):
        """Inicializa métricas do sistema."""
        self.timestamp = datetime.now()
        
        # CPU
        self.cpu_percent = 0.0
        self.cpu_count = 0
        self.cpu_freq = 0.0
        self.cpu_temp = 0.0
        
        # Memória
        self.memory_total = 0
        self.memory_used = 0
        self.memory_percent = 0.0
        self.memory_available = 0
        
        # Disco
        self.disk_total = 0
        self.disk_used = 0
        self.disk_percent = 0.0
        self.disk_free = 0
        self.disk_read_speed = 0.0
        self.disk_write_speed = 0.0
        
        # Rede
        self.network_sent = 0
        self.network_recv = 0
        self.network_sent_speed = 0.0
        self.network_recv_speed = 0.0
        
        # GPU (se disponível)
        self.gpu_percent = 0.0
        self.gpu_memory_used = 0
        self.gpu_memory_total = 0
        self.gpu_temp = 0.0
        
        # Processos
        self.process_count = 0
        self.emulator_processes = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu': {
                'percent': self.cpu_percent,
                'count': self.cpu_count,
                'freq': self.cpu_freq,
                'temp': self.cpu_temp
            },
            'memory': {
                'total': self.memory_total,
                'used': self.memory_used,
                'percent': self.memory_percent,
                'available': self.memory_available
            },
            'disk': {
                'total': self.disk_total,
                'used': self.disk_used,
                'percent': self.disk_percent,
                'free': self.disk_free,
                'read_speed': self.disk_read_speed,
                'write_speed': self.disk_write_speed
            },
            'network': {
                'sent': self.network_sent,
                'recv': self.network_recv,
                'sent_speed': self.network_sent_speed,
                'recv_speed': self.network_recv_speed
            },
            'gpu': {
                'percent': self.gpu_percent,
                'memory_used': self.gpu_memory_used,
                'memory_total': self.gpu_memory_total,
                'temp': self.gpu_temp
            },
            'processes': {
                'count': self.process_count,
                'emulator_processes': self.emulator_processes
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemMetrics':
        """Cria métricas a partir de dicionário."""
        metrics = cls()
        
        if 'timestamp' in data:
            metrics.timestamp = datetime.fromisoformat(data['timestamp'])
        
        # CPU
        cpu_data = data.get('cpu', {})
        metrics.cpu_percent = cpu_data.get('percent', 0.0)
        metrics.cpu_count = cpu_data.get('count', 0)
        metrics.cpu_freq = cpu_data.get('freq', 0.0)
        metrics.cpu_temp = cpu_data.get('temp', 0.0)
        
        # Memória
        memory_data = data.get('memory', {})
        metrics.memory_total = memory_data.get('total', 0)
        metrics.memory_used = memory_data.get('used', 0)
        metrics.memory_percent = memory_data.get('percent', 0.0)
        metrics.memory_available = memory_data.get('available', 0)
        
        # Disco
        disk_data = data.get('disk', {})
        metrics.disk_total = disk_data.get('total', 0)
        metrics.disk_used = disk_data.get('used', 0)
        metrics.disk_percent = disk_data.get('percent', 0.0)
        metrics.disk_free = disk_data.get('free', 0)
        metrics.disk_read_speed = disk_data.get('read_speed', 0.0)
        metrics.disk_write_speed = disk_data.get('write_speed', 0.0)
        
        # Rede
        network_data = data.get('network', {})
        metrics.network_sent = network_data.get('sent', 0)
        metrics.network_recv = network_data.get('recv', 0)
        metrics.network_sent_speed = network_data.get('sent_speed', 0.0)
        metrics.network_recv_speed = network_data.get('recv_speed', 0.0)
        
        # GPU
        gpu_data = data.get('gpu', {})
        metrics.gpu_percent = gpu_data.get('percent', 0.0)
        metrics.gpu_memory_used = gpu_data.get('memory_used', 0)
        metrics.gpu_memory_total = gpu_data.get('memory_total', 0)
        metrics.gpu_temp = gpu_data.get('temp', 0.0)
        
        # Processos
        processes_data = data.get('processes', {})
        metrics.process_count = processes_data.get('count', 0)
        metrics.emulator_processes = processes_data.get('emulator_processes', [])
        
        return metrics


class PerformanceAlert:
    """Alerta de performance do sistema."""
    
    def __init__(self, alert_type: str, message: str, severity: str = "warning",
                 threshold: float = 0.0, current_value: float = 0.0):
        """Inicializa alerta de performance.
        
        Args:
            alert_type: Tipo do alerta (cpu, memory, disk, etc.)
            message: Mensagem do alerta
            severity: Severidade (info, warning, critical)
            threshold: Valor limite que disparou o alerta
            current_value: Valor atual que causou o alerta
        """
        self.alert_type = alert_type
        self.message = message
        self.severity = severity
        self.threshold = threshold
        self.current_value = current_value
        self.timestamp = datetime.now()
        self.acknowledged = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte alerta para dicionário."""
        return {
            'alert_type': self.alert_type,
            'message': self.message,
            'severity': self.severity,
            'threshold': self.threshold,
            'current_value': self.current_value,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }


class SystemStatsService(BaseService):
    """Serviço para monitoramento de estatísticas e performance do sistema."""
    
    def __init__(self, monitoring_interval: float = 5.0, base_path: Optional[str] = None):
        """Inicializa o serviço de estatísticas do sistema.
        
        Args:
            monitoring_interval: Intervalo de monitoramento em segundos
            base_path: Caminho base para armazenamento de dados (opcional)
        """
        # Configurações
        self.monitoring_interval = monitoring_interval
        self.max_history_size = 1000
        self.enable_gpu_monitoring = True
        
        # Estado do monitoramento
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Histórico de métricas
        self._metrics_history: List[SystemMetrics] = []
        self._metrics_lock = threading.Lock()
        
        # Alertas
        self._alerts: List[PerformanceAlert] = []
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Limites de alerta (percentuais)
        self.cpu_warning_threshold = 80.0
        self.cpu_critical_threshold = 95.0
        self.memory_warning_threshold = 85.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 85.0
        self.disk_critical_threshold = 95.0
        self.temp_warning_threshold = 75.0
        self.temp_critical_threshold = 85.0
        
        # Cache para cálculo de velocidades
        self._last_disk_io = None
        self._last_network_io = None
        self._last_measurement_time = None
        
        # Lista de processos de emuladores conhecidos
        self.emulator_processes = [
            'retroarch', 'pcsx2', 'dolphin', 'cemu', 'yuzu', 'ryujinx',
            'ppsspp', 'desmume', 'melonds', 'mgba', 'snes9x', 'zsnes',
            'epsxe', 'project64', 'mupen64plus', 'citra', 'xenia'
        ]
        
        super().__init__()
    
    def initialize(self) -> None:
        """Inicializa o serviço de estatísticas."""
        try:
            self.logger.info("Inicializando SystemStatsService...")
            
            # Verificar disponibilidade do psutil
            if not self._check_psutil_availability():
                raise RuntimeError("psutil não está disponível")
            
            # Coletar métricas iniciais
            initial_metrics = self._collect_metrics()
            if initial_metrics:
                with self._metrics_lock:
                    self._metrics_history.append(initial_metrics)
            
            self.logger.info("SystemStatsService inicializado")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar SystemStatsService: {e}")
            raise
    
    def start_monitoring(self) -> bool:
        """Inicia o monitoramento contínuo do sistema.
        
        Returns:
            True se iniciou com sucesso
        """
        try:
            if self._monitoring_active:
                self.logger.warning("Monitoramento já está ativo")
                return True
            
            self._stop_event.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="SystemStatsMonitoring"
            )
            
            self._monitoring_thread.start()
            self._monitoring_active = True
            
            self.logger.info("Monitoramento de sistema iniciado")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar monitoramento: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Para o monitoramento contínuo do sistema.
        
        Returns:
            True se parou com sucesso
        """
        try:
            if not self._monitoring_active:
                self.logger.warning("Monitoramento não está ativo")
                return True
            
            self._stop_event.set()
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10.0)
            
            self._monitoring_active = False
            self.logger.info("Monitoramento de sistema parado")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao parar monitoramento: {e}")
            return False
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Obtém métricas atuais do sistema.
        
        Returns:
            Métricas atuais ou None se erro
        """
        return self._collect_metrics()
    
    def get_metrics_history(self, hours: int = 1) -> List[SystemMetrics]:
        """Obtém histórico de métricas.
        
        Args:
            hours: Número de horas de histórico
            
        Returns:
            Lista de métricas no período
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._metrics_lock:
            return [m for m in self._metrics_history if m.timestamp >= cutoff_time]
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Obtém resumo de performance do sistema.
        
        Args:
            hours: Período para análise em horas
            
        Returns:
            Dicionário com resumo de performance
        """
        try:
            metrics_list = self.get_metrics_history(hours)
            
            if not metrics_list:
                return {}
            
            # Calcular estatísticas
            cpu_values = [m.cpu_percent for m in metrics_list]
            memory_values = [m.memory_percent for m in metrics_list]
            disk_values = [m.disk_percent for m in metrics_list]
            
            summary = {
                'period_hours': hours,
                'sample_count': len(metrics_list),
                'cpu': {
                    'avg': sum(cpu_values) / len(cpu_values),
                    'min': min(cpu_values),
                    'max': max(cpu_values),
                    'current': cpu_values[-1] if cpu_values else 0
                },
                'memory': {
                    'avg': sum(memory_values) / len(memory_values),
                    'min': min(memory_values),
                    'max': max(memory_values),
                    'current': memory_values[-1] if memory_values else 0
                },
                'disk': {
                    'avg': sum(disk_values) / len(disk_values),
                    'min': min(disk_values),
                    'max': max(disk_values),
                    'current': disk_values[-1] if disk_values else 0
                },
                'emulator_activity': self._analyze_emulator_activity(metrics_list),
                'alerts_count': len([a for a in self._alerts 
                                   if a.timestamp >= datetime.now() - timedelta(hours=hours)])
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo de performance: {e}")
            return {}
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Obtém alertas ativos (não reconhecidos).
        
        Returns:
            Lista de alertas ativos
        """
        return [alert for alert in self._alerts if not alert.acknowledged]
    
    def acknowledge_alert(self, alert_index: int) -> bool:
        """Reconhece um alerta.
        
        Args:
            alert_index: Índice do alerta na lista
            
        Returns:
            True se reconheceu com sucesso
        """
        try:
            if 0 <= alert_index < len(self._alerts):
                self._alerts[alert_index].acknowledged = True
                self.logger.info(f"Alerta {alert_index} reconhecido")
                return True
            else:
                self.logger.warning(f"Índice de alerta inválido: {alert_index}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao reconhecer alerta: {e}")
            return False
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Adiciona callback para notificação de alertas.
        
        Args:
            callback: Função a ser chamada quando houver novo alerta
        """
        self._alert_callbacks.append(callback)
    
    def export_metrics(self, file_path: str, hours: int = 24) -> bool:
        """Exporta métricas para arquivo JSON.
        
        Args:
            file_path: Caminho do arquivo de destino
            hours: Período para exportação em horas
            
        Returns:
            True se exportou com sucesso
        """
        try:
            metrics_list = self.get_metrics_history(hours)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'period_hours': hours,
                'metrics_count': len(metrics_list),
                'metrics': [m.to_dict() for m in metrics_list],
                'summary': self.get_performance_summary(hours)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Métricas exportadas para {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao exportar métricas: {e}")
            return False
    
    def _check_psutil_availability(self) -> bool:
        """Verifica se psutil está disponível e funcionando."""
        try:
            psutil.cpu_percent()
            psutil.virtual_memory()
            psutil.disk_usage('/')
            return True
        except Exception as e:
            self.logger.error(f"psutil não está funcionando: {e}")
            return False
    
    def _collect_metrics(self) -> Optional[SystemMetrics]:
        """Coleta métricas atuais do sistema."""
        try:
            metrics = SystemMetrics()
            
            # CPU
            metrics.cpu_percent = psutil.cpu_percent(interval=1)
            metrics.cpu_count = psutil.cpu_count()
            
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                metrics.cpu_freq = cpu_freq.current
            
            # Temperatura da CPU (se disponível)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            if entries:
                                metrics.cpu_temp = entries[0].current
                                break
            except:
                pass
            
            # Memória
            memory = psutil.virtual_memory()
            metrics.memory_total = memory.total
            metrics.memory_used = memory.used
            metrics.memory_percent = memory.percent
            metrics.memory_available = memory.available
            
            # Disco (drive principal)
            try:
                disk = psutil.disk_usage('/')
                metrics.disk_total = disk.total
                metrics.disk_used = disk.used
                metrics.disk_percent = (disk.used / disk.total) * 100
                metrics.disk_free = disk.free
            except:
                # Fallback para Windows
                try:
                    disk = psutil.disk_usage('C:')
                    metrics.disk_total = disk.total
                    metrics.disk_used = disk.used
                    metrics.disk_percent = (disk.used / disk.total) * 100
                    metrics.disk_free = disk.free
                except:
                    pass
            
            # I/O de disco
            current_time = time.time()
            disk_io = psutil.disk_io_counters()
            
            if disk_io and self._last_disk_io and self._last_measurement_time:
                time_diff = current_time - self._last_measurement_time
                if time_diff > 0:
                    read_diff = disk_io.read_bytes - self._last_disk_io.read_bytes
                    write_diff = disk_io.write_bytes - self._last_disk_io.write_bytes
                    
                    metrics.disk_read_speed = read_diff / time_diff
                    metrics.disk_write_speed = write_diff / time_diff
            
            self._last_disk_io = disk_io
            
            # Rede
            network_io = psutil.net_io_counters()
            if network_io:
                metrics.network_sent = network_io.bytes_sent
                metrics.network_recv = network_io.bytes_recv
                
                if self._last_network_io and self._last_measurement_time:
                    time_diff = current_time - self._last_measurement_time
                    if time_diff > 0:
                        sent_diff = network_io.bytes_sent - self._last_network_io.bytes_sent
                        recv_diff = network_io.bytes_recv - self._last_network_io.bytes_recv
                        
                        metrics.network_sent_speed = sent_diff / time_diff
                        metrics.network_recv_speed = recv_diff / time_diff
                
                self._last_network_io = network_io
            
            self._last_measurement_time = current_time
            
            # GPU (se disponível)
            if self.enable_gpu_monitoring:
                self._collect_gpu_metrics(metrics)
            
            # Processos
            metrics.process_count = len(psutil.pids())
            metrics.emulator_processes = self._get_emulator_processes()
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Erro ao coletar métricas: {e}")
            return None
    
    def _collect_gpu_metrics(self, metrics: SystemMetrics) -> None:
        """Coleta métricas da GPU se disponível."""
        try:
            # Tentar usar nvidia-ml-py se disponível
            try:
                import pynvml
                pynvml.nvmlInit()
                
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                
                # Utilização da GPU
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                metrics.gpu_percent = util.gpu
                
                # Memória da GPU
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                metrics.gpu_memory_total = mem_info.total
                metrics.gpu_memory_used = mem_info.used
                
                # Temperatura da GPU
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                metrics.gpu_temp = temp
                
            except ImportError:
                # pynvml não disponível
                pass
            except Exception:
                # Erro ao acessar GPU NVIDIA
                pass
                
        except Exception as e:
            self.logger.debug(f"Não foi possível coletar métricas da GPU: {e}")
    
    def _get_emulator_processes(self) -> List[Dict[str, Any]]:
        """Obtém lista de processos de emuladores ativos."""
        emulator_procs = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    
                    for emulator in self.emulator_processes:
                        if emulator in proc_name:
                            emulator_procs.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'emulator': emulator,
                                'cpu_percent': proc.info['cpu_percent'] or 0,
                                'memory_percent': proc.info['memory_percent'] or 0
                            })
                            break
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Erro ao obter processos de emuladores: {e}")
        
        return emulator_procs
    
    def _monitoring_loop(self) -> None:
        """Loop principal de monitoramento."""
        self.logger.info("Loop de monitoramento iniciado")
        
        while not self._stop_event.is_set():
            try:
                # Coletar métricas
                metrics = self._collect_metrics()
                
                if metrics:
                    # Adicionar ao histórico
                    with self._metrics_lock:
                        self._metrics_history.append(metrics)
                        
                        # Limitar tamanho do histórico
                        if len(self._metrics_history) > self.max_history_size:
                            self._metrics_history = self._metrics_history[-self.max_history_size:]
                    
                    # Verificar alertas
                    self._check_alerts(metrics)
                
                # Aguardar próximo ciclo
                self._stop_event.wait(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento: {e}")
                self._stop_event.wait(self.monitoring_interval)
        
        self.logger.info("Loop de monitoramento finalizado")
    
    def _check_alerts(self, metrics: SystemMetrics) -> None:
        """Verifica se métricas excedem limites e gera alertas."""
        try:
            # CPU
            if metrics.cpu_percent >= self.cpu_critical_threshold:
                self._create_alert(
                    "cpu", f"CPU crítica: {metrics.cpu_percent:.1f}%", "critical",
                    self.cpu_critical_threshold, metrics.cpu_percent
                )
            elif metrics.cpu_percent >= self.cpu_warning_threshold:
                self._create_alert(
                    "cpu", f"CPU alta: {metrics.cpu_percent:.1f}%", "warning",
                    self.cpu_warning_threshold, metrics.cpu_percent
                )
            
            # Memória
            if metrics.memory_percent >= self.memory_critical_threshold:
                self._create_alert(
                    "memory", f"Memória crítica: {metrics.memory_percent:.1f}%", "critical",
                    self.memory_critical_threshold, metrics.memory_percent
                )
            elif metrics.memory_percent >= self.memory_warning_threshold:
                self._create_alert(
                    "memory", f"Memória alta: {metrics.memory_percent:.1f}%", "warning",
                    self.memory_warning_threshold, metrics.memory_percent
                )
            
            # Disco
            if metrics.disk_percent >= self.disk_critical_threshold:
                self._create_alert(
                    "disk", f"Disco crítico: {metrics.disk_percent:.1f}%", "critical",
                    self.disk_critical_threshold, metrics.disk_percent
                )
            elif metrics.disk_percent >= self.disk_warning_threshold:
                self._create_alert(
                    "disk", f"Disco cheio: {metrics.disk_percent:.1f}%", "warning",
                    self.disk_warning_threshold, metrics.disk_percent
                )
            
            # Temperatura
            if metrics.cpu_temp > 0:
                if metrics.cpu_temp >= self.temp_critical_threshold:
                    self._create_alert(
                        "temperature", f"Temperatura crítica: {metrics.cpu_temp:.1f}°C", "critical",
                        self.temp_critical_threshold, metrics.cpu_temp
                    )
                elif metrics.cpu_temp >= self.temp_warning_threshold:
                    self._create_alert(
                        "temperature", f"Temperatura alta: {metrics.cpu_temp:.1f}°C", "warning",
                        self.temp_warning_threshold, metrics.cpu_temp
                    )
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar alertas: {e}")
    
    def _create_alert(self, alert_type: str, message: str, severity: str,
                     threshold: float, current_value: float) -> None:
        """Cria novo alerta se não existir similar recente."""
        try:
            # Verificar se já existe alerta similar nos últimos 5 minutos
            cutoff_time = datetime.now() - timedelta(minutes=5)
            recent_alerts = [a for a in self._alerts 
                           if a.alert_type == alert_type and a.timestamp >= cutoff_time]
            
            if recent_alerts:
                return  # Não criar alerta duplicado
            
            # Criar novo alerta
            alert = PerformanceAlert(alert_type, message, severity, threshold, current_value)
            self._alerts.append(alert)
            
            # Limitar número de alertas
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]
            
            # Notificar callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Erro em callback de alerta: {e}")
            
            self.logger.warning(f"Alerta criado: {message}")
            
        except Exception as e:
            self.logger.error(f"Erro ao criar alerta: {e}")
    
    def _analyze_emulator_activity(self, metrics_list: List[SystemMetrics]) -> Dict[str, Any]:
        """Analisa atividade de emuladores no período."""
        try:
            if not metrics_list:
                return {}
            
            emulator_stats = {}
            total_samples = len(metrics_list)
            
            for metrics in metrics_list:
                for proc in metrics.emulator_processes:
                    emulator = proc['emulator']
                    
                    if emulator not in emulator_stats:
                        emulator_stats[emulator] = {
                            'active_samples': 0,
                            'total_cpu': 0.0,
                            'total_memory': 0.0,
                            'max_cpu': 0.0,
                            'max_memory': 0.0
                        }
                    
                    stats = emulator_stats[emulator]
                    stats['active_samples'] += 1
                    stats['total_cpu'] += proc['cpu_percent']
                    stats['total_memory'] += proc['memory_percent']
                    stats['max_cpu'] = max(stats['max_cpu'], proc['cpu_percent'])
                    stats['max_memory'] = max(stats['max_memory'], proc['memory_percent'])
            
            # Calcular médias e percentuais de atividade
            for emulator, stats in emulator_stats.items():
                if stats['active_samples'] > 0:
                    stats['avg_cpu'] = stats['total_cpu'] / stats['active_samples']
                    stats['avg_memory'] = stats['total_memory'] / stats['active_samples']
                    stats['activity_percent'] = (stats['active_samples'] / total_samples) * 100
                else:
                    stats['avg_cpu'] = 0.0
                    stats['avg_memory'] = 0.0
                    stats['activity_percent'] = 0.0
            
            return emulator_stats
            
        except Exception as e:
            self.logger.error(f"Erro ao analisar atividade de emuladores: {e}")
            return {}