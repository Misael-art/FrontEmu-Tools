"""System Utilities Module.

Provides utilities for system information, drive management, and performance monitoring.
"""

import logging
import os
import platform
import psutil
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .admin_utils import is_admin


class SystemUtils:
    """Utilities for system operations and information gathering."""

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Obtém informações básicas do sistema.
        
        Returns:
            Dict contendo informações do sistema (OS, arquitetura, versão, etc.)
        """
        try:
            return {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            logging.error(f"Error getting system info: {e}")
            return {"error": str(e)}

    @staticmethod
    def is_admin_required_for_path(path: str) -> bool:
        """
        Verifica se privilégios administrativos são necessários para acessar um caminho.
        
        Args:
            path: Caminho a ser verificado
            
        Returns:
            True se privilégios administrativos são necessários
        """
        try:
            path_obj = Path(path)
            
            # Verifica se o caminho está em diretórios do sistema
            system_paths = [
                "C:\\Windows",
                "C:\\Program Files",
                "C:\\Program Files (x86)",
                "C:\\ProgramData"
            ]
            
            path_str = str(path_obj.resolve()).upper()
            for sys_path in system_paths:
                if path_str.startswith(sys_path.upper()):
                    return True
            
            # Tenta criar um arquivo temporário para testar permissões
            if path_obj.is_dir():
                test_file = path_obj / f"test_permissions_{int(time.time())}.tmp"
                try:
                    test_file.touch()
                    test_file.unlink()
                    return False
                except (PermissionError, OSError):
                    return True
            else:
                # Para arquivos, testa o diretório pai
                return SystemUtils.is_admin_required_for_path(str(path_obj.parent))
                
        except Exception:
            # Em caso de erro, assume que privilégios são necessários
            return True

    @staticmethod
    def get_current_user_info() -> Dict[str, Any]:
        """
        Obtém informações do usuário atual.
        
        Returns:
            Dict contendo informações do usuário
        """
        try:
            return {
                "username": os.getenv("USERNAME", "unknown"),
                "user_domain": os.getenv("USERDOMAIN", "unknown"),
                "user_profile": os.getenv("USERPROFILE", "unknown"),
                "is_admin": is_admin(),
                "temp_dir": os.getenv("TEMP", "unknown"),
                "app_data": os.getenv("APPDATA", "unknown"),
                "local_app_data": os.getenv("LOCALAPPDATA", "unknown")
            }
        except Exception as e:
            logging.error(f"Error getting user info: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_environment_variables() -> Dict[str, str]:
        """
        Obtém variáveis de ambiente relevantes.
        
        Returns:
            Dict contendo variáveis de ambiente
        """
        relevant_vars = [
            "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "APPDATA",
            "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA",
            "SYSTEMROOT", "WINDIR", "COMPUTERNAME", "USERNAME", "USERDOMAIN"
        ]
        
        return {var: os.getenv(var, "") for var in relevant_vars}

    @staticmethod
    def check_process_running(process_name: str) -> bool:
        """
        Verifica se um processo está em execução.
        
        Args:
            process_name: Nome do processo a verificar
            
        Returns:
            True se o processo está em execução
        """
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    return True
            return False
        except Exception as e:
            logging.error(f"Error checking process {process_name}: {e}")
            return False

    @staticmethod
    def get_running_processes() -> List[Dict[str, Any]]:
        """
        Obtém lista de processos em execução.
        
        Returns:
            Lista de dicionários com informações dos processos
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "memory_mb": proc.info['memory_info'].rss / 1024 / 1024 if proc.info['memory_info'] else 0,
                        "cpu_percent": proc.info['cpu_percent'] or 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes
        except Exception as e:
            logging.error(f"Error getting running processes: {e}")
            return []

    @staticmethod
    def get_system_performance() -> Dict[str, Any]:
        """
        Obtém métricas de performance do sistema.
        
        Returns:
            Dict contendo métricas de performance
        """
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "memory_used": memory.used,
                "disk_percent": disk.percent if hasattr(disk, 'percent') else 0,
                "disk_free": disk.free if hasattr(disk, 'free') else 0,
                "disk_used": disk.used if hasattr(disk, 'used') else 0,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                "active_processes": len(psutil.pids())
            }
        except Exception as e:
            logging.error(f"Error getting system performance: {e}")
            return {"error": str(e)}

    @staticmethod
    def execute_command(command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Executa um comando do sistema.
        
        Args:
            command: Comando a ser executado
            timeout: Timeout em segundos
            
        Returns:
            Tupla (sucesso, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def get_installed_software() -> List[Dict[str, str]]:
        """
        Obtém lista de software instalado (Windows).
        
        Returns:
            Lista de dicionários com informações do software
        """
        try:
            if platform.system() != "Windows":
                return []
                
            software_list = []
            
            # Verifica registro do Windows para software instalado
            try:
                import winreg
                
                # Chaves do registro onde software instalado é listado
                registry_keys = [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
                ]
                
                for key_path in registry_keys:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, subkey_name) as subkey:
                                        try:
                                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                            version = ""
                                            publisher = ""
                                            
                                            try:
                                                version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                            except FileNotFoundError:
                                                pass
                                                
                                            try:
                                                publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                                            except FileNotFoundError:
                                                pass
                                            
                                            software_list.append({
                                                "name": name,
                                                "version": version,
                                                "publisher": publisher
                                            })
                                        except FileNotFoundError:
                                            continue
                                except OSError:
                                    continue
                    except OSError:
                        continue
                        
            except ImportError:
                logging.warning("winreg module not available")
                
            return software_list
            
        except Exception as e:
            logging.error(f"Error getting installed software: {e}")
            return []