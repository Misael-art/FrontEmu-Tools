"""
Infrastructure Adapters

Adaptadores para serviços externos que implementam as interfaces
definidas na camada de domínio.
"""

import os
import platform
import psutil
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..domain.entities import DriveInfo, DriveType, SystemMetrics
from ..domain.use_cases import FileSystemService, SystemMonitoringService


class FileSystemServiceImpl(FileSystemService):
    """Implementação do serviço de sistema de arquivos."""
    
    def get_drive_info(self, drive_letter: str) -> Optional[DriveInfo]:
        """Obtém informações de um drive."""
        try:
            # Normalizar letra do drive
            if not drive_letter.endswith(':'):
                drive_letter += ':'
            
            # Verificar se o drive existe
            if not Path(drive_letter).exists():
                return None
            
            # Obter informações usando psutil
            try:
                usage = psutil.disk_usage(drive_letter)
                partitions = psutil.disk_partitions()
                
                # Encontrar partição correspondente
                partition_info = None
                for partition in partitions:
                    if partition.device.upper() == drive_letter.upper():
                        partition_info = partition
                        break
                
                if not partition_info:
                    return None
                
                # Determinar tipo do drive
                drive_type = self._get_drive_type(partition_info)
                
                # Obter label do volume
                label = self._get_volume_label(drive_letter)
                
                return DriveInfo(
                    letter=drive_letter.replace(':', ''),
                    label=label,
                    file_system=partition_info.fstype,
                    drive_type=drive_type,
                    total_space=usage.total,
                    free_space=usage.free,
                    is_ready=True
                )
                
            except (PermissionError, OSError):
                # Drive não está pronto ou não acessível
                return DriveInfo(
                    letter=drive_letter.replace(':', ''),
                    label="",
                    file_system="",
                    drive_type=DriveType.UNKNOWN,
                    total_space=0,
                    free_space=0,
                    is_ready=False
                )
                
        except Exception:
            return None
    
    def scan_directory(self, path: str, extensions: Set[str]) -> List[str]:
        """Escaneia diretório por arquivos com extensões específicas."""
        try:
            found_files = []
            path_obj = Path(path)
            
            if not path_obj.exists() or not path_obj.is_dir():
                return found_files
            
            # Normalizar extensões (adicionar ponto se necessário)
            normalized_extensions = set()
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                normalized_extensions.add(ext.lower())
            
            # Buscar arquivos recursivamente
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    
                    # Verificar se é um arquivo específico (sem extensão)
                    file_name = file_path.name.lower()
                    
                    if file_ext in normalized_extensions or file_name in {e.lstrip('.') for e in extensions}:
                        found_files.append(str(file_path))
            
            return found_files
            
        except Exception:
            return []
    
    def copy_file(self, source: str, destination: str) -> bool:
        """Copia arquivo."""
        try:
            source_path = Path(source)
            destination_path = Path(destination)
            
            if not source_path.exists() or not source_path.is_file():
                return False
            
            # Criar diretório de destino se necessário
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copiar arquivo
            shutil.copy2(source, destination)
            
            # Verificar se a cópia foi bem-sucedida
            return destination_path.exists() and destination_path.stat().st_size > 0
            
        except Exception:
            return False
    
    def move_file(self, source: str, destination: str) -> bool:
        """Move arquivo."""
        try:
            source_path = Path(source)
            destination_path = Path(destination)
            
            if not source_path.exists() or not source_path.is_file():
                return False
            
            # Criar diretório de destino se necessário
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Mover arquivo
            shutil.move(source, destination)
            
            # Verificar se o movimento foi bem-sucedido
            return destination_path.exists() and not source_path.exists()
            
        except Exception:
            return False
    
    def create_directory(self, path: str) -> bool:
        """Cria diretório."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return Path(path).exists()
        except Exception:
            return False
    
    def _get_drive_type(self, partition_info) -> DriveType:
        """Determina o tipo do drive baseado nas informações da partição."""
        try:
            device = partition_info.device.upper()
            opts = partition_info.opts.lower() if partition_info.opts else ""
            
            # Verificar se é drive de rede
            if 'remote' in opts or device.startswith('\\\\'):
                return DriveType.NETWORK
            
            # Verificar se é CD/DVD
            if 'cdrom' in opts or partition_info.fstype.lower() in ['cdfs', 'udf']:
                return DriveType.CDROM
            
            # Verificar se é removível (USB, etc.)
            if 'removable' in opts:
                return DriveType.REMOVABLE
            
            # Verificar se é RAM disk
            if 'ram' in opts or device.startswith('RAM'):
                return DriveType.RAM
            
            # Por padrão, considerar como disco fixo
            return DriveType.FIXED
            
        except Exception:
            return DriveType.UNKNOWN
    
    def _get_volume_label(self, drive_letter: str) -> str:
        """Obtém o label do volume no Windows."""
        try:
            if platform.system() == "Windows":
                import subprocess
                
                # Usar comando vol para obter label
                result = subprocess.run(
                    ['vol', drive_letter],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    lines = output.split('\n')
                    
                    for line in lines:
                        if 'Volume in drive' in line and 'is' in line:
                            # Extrair label da linha
                            parts = line.split(' is ')
                            if len(parts) > 1:
                                return parts[1].strip()
                
            return ""
            
        except Exception:
            return ""


class SystemMonitoringServiceImpl(SystemMonitoringService):
    """Implementação do serviço de monitoramento do sistema."""
    
    def __init__(self):
        """Inicializa o serviço de monitoramento."""
        self._last_cpu_times = None
        self._last_network_io = None
        self._last_disk_io = None
        self._last_check_time = None
    
    def get_current_metrics(self) -> SystemMetrics:
        """Obtém métricas atuais do sistema."""
        try:
            current_time = time.time()
            
            # CPU
            cpu_usage = self._get_cpu_usage()
            cpu_temperature = self._get_cpu_temperature()
            
            # Memória
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_total = memory.total
            memory_available = memory.available
            
            # Disco
            disk_usage = self._get_disk_usage()
            disk_read_speed, disk_write_speed = self._get_disk_io_speed()
            
            # Rede
            network_upload_speed, network_download_speed = self._get_network_speed()
            
            # GPU (se disponível)
            gpu_usage, gpu_temperature = self._get_gpu_metrics()
            
            # Processos
            process_count = len(psutil.pids())
            
            self._last_check_time = current_time
            
            return SystemMetrics(
                timestamp=current_time,
                cpu_usage=cpu_usage,
                cpu_temperature=cpu_temperature,
                memory_usage=memory_usage,
                memory_total=memory_total,
                memory_available=memory_available,
                disk_usage=disk_usage,
                disk_read_speed=disk_read_speed,
                disk_write_speed=disk_write_speed,
                network_upload_speed=network_upload_speed,
                network_download_speed=network_download_speed,
                gpu_usage=gpu_usage,
                gpu_temperature=gpu_temperature,
                process_count=process_count
            )
            
        except Exception:
            # Retornar métricas padrão em caso de erro
            return SystemMetrics(
                timestamp=time.time(),
                cpu_usage=0.0,
                cpu_temperature=0.0,
                memory_usage=0.0,
                memory_total=0,
                memory_available=0,
                disk_usage=0.0,
                disk_read_speed=0.0,
                disk_write_speed=0.0,
                network_upload_speed=0.0,
                network_download_speed=0.0,
                gpu_usage=0.0,
                gpu_temperature=0.0,
                process_count=0
            )
    
    def get_running_processes(self) -> List[str]:
        """Obtém processos em execução."""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['name']:
                        processes.append(
                            f"{proc_info['name']} (PID: {proc_info['pid']}, "
                            f"CPU: {proc_info['cpu_percent']:.1f}%, "
                            f"MEM: {proc_info['memory_percent']:.1f}%)"
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return sorted(processes)
            
        except Exception:
            return []
    
    def _get_cpu_usage(self) -> float:
        """Obtém uso da CPU."""
        try:
            # Usar intervalo de 1 segundo para medição mais precisa
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def _get_cpu_temperature(self) -> float:
        """Obtém temperatura da CPU."""
        try:
            # Tentar obter temperatura usando psutil
            temps = psutil.sensors_temperatures()
            
            if temps:
                # Procurar por sensores de CPU
                for name, entries in temps.items():
                    if 'cpu' in name.lower() or 'core' in name.lower():
                        if entries:
                            return entries[0].current
                
                # Se não encontrou CPU específico, usar primeiro sensor disponível
                for name, entries in temps.items():
                    if entries:
                        return entries[0].current
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _get_disk_usage(self) -> float:
        """Obtém uso do disco principal."""
        try:
            # Usar disco principal (C: no Windows, / no Linux)
            if platform.system() == "Windows":
                disk_path = "C:\\"
            else:
                disk_path = "/"
            
            usage = psutil.disk_usage(disk_path)
            return (usage.used / usage.total) * 100
            
        except Exception:
            return 0.0
    
    def _get_disk_io_speed(self) -> tuple[float, float]:
        """Obtém velocidade de I/O do disco."""
        try:
            current_io = psutil.disk_io_counters()
            current_time = time.time()
            
            if self._last_disk_io and self._last_check_time:
                time_delta = current_time - self._last_check_time
                
                if time_delta > 0:
                    read_speed = (current_io.read_bytes - self._last_disk_io.read_bytes) / time_delta
                    write_speed = (current_io.write_bytes - self._last_disk_io.write_bytes) / time_delta
                    
                    self._last_disk_io = current_io
                    return read_speed, write_speed
            
            self._last_disk_io = current_io
            return 0.0, 0.0
            
        except Exception:
            return 0.0, 0.0
    
    def _get_network_speed(self) -> tuple[float, float]:
        """Obtém velocidade da rede."""
        try:
            current_io = psutil.net_io_counters()
            current_time = time.time()
            
            if self._last_network_io and self._last_check_time:
                time_delta = current_time - self._last_check_time
                
                if time_delta > 0:
                    upload_speed = (current_io.bytes_sent - self._last_network_io.bytes_sent) / time_delta
                    download_speed = (current_io.bytes_recv - self._last_network_io.bytes_recv) / time_delta
                    
                    self._last_network_io = current_io
                    return upload_speed, download_speed
            
            self._last_network_io = current_io
            return 0.0, 0.0
            
        except Exception:
            return 0.0, 0.0
    
    def _get_gpu_metrics(self) -> tuple[float, float]:
        """Obtém métricas da GPU."""
        try:
            # Tentar usar nvidia-ml-py para GPUs NVIDIA
            try:
                import pynvml
                
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    
                    # Uso da GPU
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_usage = utilization.gpu
                    
                    # Temperatura da GPU
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    
                    return float(gpu_usage), float(temperature)
                    
            except ImportError:
                # pynvml não está disponível
                pass
            except Exception:
                # Erro ao acessar GPU NVIDIA
                pass
            
            # Tentar métodos alternativos para outras GPUs
            # Por enquanto, retornar valores padrão
            return 0.0, 0.0
            
        except Exception:
            return 0.0, 0.0


class WindowsSpecificAdapter:
    """Adaptador específico para funcionalidades do Windows."""
    
    @staticmethod
    def get_drive_letters() -> List[str]:
        """Obtém todas as letras de drive disponíveis no Windows."""
        try:
            if platform.system() != "Windows":
                return []
            
            import string
            available_drives = []
            
            for letter in string.ascii_uppercase:
                drive_path = f"{letter}:\\"
                if os.path.exists(drive_path):
                    available_drives.append(letter)
            
            return available_drives
            
        except Exception:
            return []
    
    @staticmethod
    def get_registry_value(key_path: str, value_name: str) -> Optional[str]:
        """Obtém valor do registro do Windows."""
        try:
            if platform.system() != "Windows":
                return None
            
            import winreg
            
            # Tentar diferentes hives
            hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
            
            for hive in hives:
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        value, _ = winreg.QueryValueEx(key, value_name)
                        return str(value)
                except FileNotFoundError:
                    continue
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def is_admin() -> bool:
        """Verifica se o processo está executando como administrador."""
        try:
            if platform.system() != "Windows":
                return os.geteuid() == 0  # Para sistemas Unix-like
            
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
            
        except Exception:
            return False


class CrossPlatformAdapter:
    """Adaptador multiplataforma para funcionalidades comuns."""
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """Obtém informações básicas do sistema."""
        try:
            return {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            }
        except Exception:
            return {}
    
    @staticmethod
    def get_environment_variables() -> Dict[str, str]:
        """Obtém variáveis de ambiente relevantes."""
        try:
            relevant_vars = [
                "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA",
                "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
                "SYSTEMROOT", "WINDIR", "HOME", "USER", "USERNAME"
            ]
            
            env_vars = {}
            for var in relevant_vars:
                value = os.environ.get(var)
                if value:
                    env_vars[var] = value
            
            return env_vars
            
        except Exception:
            return {}
    
    @staticmethod
    def get_installed_software() -> List[str]:
        """Obtém lista de software instalado."""
        try:
            software_list = []
            
            if platform.system() == "Windows":
                # Usar registro do Windows para listar software instalado
                try:
                    import winreg
                    
                    uninstall_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                    
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                        software_list.append(display_name)
                                    except FileNotFoundError:
                                        continue
                            except Exception:
                                continue
                                
                except Exception:
                    pass
            
            return sorted(software_list)
            
        except Exception:
            return []