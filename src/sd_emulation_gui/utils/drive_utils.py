"""Drive Utilities Module.

Provides utilities for drive operations, space checking, and drive management.
"""

import logging
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32api
    import win32file
except ImportError:
    win32api = None
    win32file = None


@dataclass
class DriveInfo:
    """Informações de um drive do sistema."""
    letter: str
    label: str
    file_system: str
    total_space: int
    free_space: int
    used_space: int
    usage_percentage: float
    is_ready: bool
    drive_type: str

    def __post_init__(self):
        """Calcula a porcentagem de uso após inicialização."""
        if self.total_space > 0:
            self.usage_percentage = (self.used_space / self.total_space) * 100
        else:
            self.usage_percentage = 0.0


@dataclass
class SpaceCheckResult:
    """Resultado da verificação de espaço em disco."""
    has_sufficient_space: bool
    available_space: int
    required_space: int
    shortage_amount: int
    recommendations: List[str]

    @classmethod
    def create_success(cls, available: int, required: int) -> 'SpaceCheckResult':
        """Cria resultado de sucesso."""
        return cls(
            has_sufficient_space=True,
            available_space=available,
            required_space=required,
            shortage_amount=0,
            recommendations=[]
        )

    @classmethod
    def create_failure(cls, available: int, required: int, recommendations: List[str]) -> 'SpaceCheckResult':
        """Cria resultado de falha."""
        return cls(
            has_sufficient_space=False,
            available_space=available,
            required_space=required,
            shortage_amount=required - available,
            recommendations=recommendations
        )


@dataclass
class DriveValidationResult:
    """Resultado da validação de um drive."""
    is_valid: bool
    drive_path: str
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]


class DriveUtils:
    """Utilities for drive operations and management."""

    # Tipos de drive conhecidos
    DRIVE_TYPES = {
        0: "unknown",
        1: "removable",
        2: "fixed",
        3: "network",
        4: "cdrom",
        5: "ramdisk"
    }

    @staticmethod
    def get_drive_letter(path: str) -> str:
        """
        Extrai a letra do drive de um caminho.
        
        Args:
            path: Caminho do arquivo ou diretório
            
        Returns:
            Letra do drive (ex: "C:")
        """
        try:
            path_obj = Path(path).resolve()
            if os.name == 'nt':  # Windows
                return str(path_obj).split(':')[0] + ':'
            else:
                return '/'
        except Exception as e:
            logging.error(f"Error extracting drive letter from {path}: {e}")
            return ""

    @staticmethod
    def is_same_drive(path1: str, path2: str) -> bool:
        """
        Verifica se dois caminhos estão no mesmo drive.
        
        Args:
            path1: Primeiro caminho
            path2: Segundo caminho
            
        Returns:
            True se estão no mesmo drive
        """
        try:
            drive1 = DriveUtils.get_drive_letter(path1)
            drive2 = DriveUtils.get_drive_letter(path2)
            return drive1.upper() == drive2.upper()
        except Exception as e:
            logging.error(f"Error comparing drives for {path1} and {path2}: {e}")
            return False

    @staticmethod
    def get_drive_root(path: str) -> str:
        """
        Obtém a raiz do drive para um caminho.
        
        Args:
            path: Caminho do arquivo ou diretório
            
        Returns:
            Raiz do drive (ex: "C:\\")
        """
        try:
            if os.name == 'nt':  # Windows
                drive_letter = DriveUtils.get_drive_letter(path)
                return drive_letter + "\\"
            else:
                return "/"
        except Exception as e:
            logging.error(f"Error getting drive root for {path}: {e}")
            return ""

    @staticmethod
    def get_drive_type(drive_path: str) -> str:
        """
        Determina o tipo do drive.
        
        Args:
            drive_path: Caminho do drive (ex: "C:")
            
        Returns:
            Tipo do drive ("fixed", "removable", "network", etc.)
        """
        try:
            if os.name == 'nt' and win32file:  # Windows
                drive_type = win32file.GetDriveType(drive_path + "\\")
                return DriveUtils.DRIVE_TYPES.get(drive_type, "unknown")
            else:
                # Para sistemas não-Windows, assume fixed
                return "fixed"
        except Exception as e:
            logging.error(f"Error getting drive type for {drive_path}: {e}")
            return "unknown"

    @staticmethod
    def get_drive_info(drive_path: str) -> Optional[DriveInfo]:
        """
        Obtém informações detalhadas de um drive.
        
        Args:
            drive_path: Caminho do drive (ex: "C:")
            
        Returns:
            DriveInfo com informações do drive ou None se erro
        """
        try:
            # Normaliza o caminho do drive
            if os.name == 'nt':
                if not drive_path.endswith(':'):
                    drive_path = drive_path.rstrip('\\') + ':'
                root_path = drive_path + "\\"
            else:
                root_path = drive_path

            # Verifica se o drive está acessível
            if not os.path.exists(root_path):
                return None

            # Obtém informações de espaço
            try:
                total, used, free = shutil.disk_usage(root_path)
            except Exception:
                return None

            # Obtém label do drive
            label = ""
            if os.name == 'nt' and win32api:
                try:
                    label = win32api.GetVolumeInformation(root_path)[0] or ""
                except Exception:
                    pass

            # Obtém sistema de arquivos
            file_system = ""
            if os.name == 'nt' and win32api:
                try:
                    file_system = win32api.GetVolumeInformation(root_path)[4] or ""
                except Exception:
                    pass

            # Obtém tipo do drive
            drive_type = DriveUtils.get_drive_type(drive_path)

            return DriveInfo(
                letter=drive_path,
                label=label,
                file_system=file_system,
                total_space=total,
                free_space=free,
                used_space=used,
                usage_percentage=0.0,  # Será calculado no __post_init__
                is_ready=True,
                drive_type=drive_type
            )

        except Exception as e:
            logging.error(f"Error getting drive info for {drive_path}: {e}")
            return None

    @staticmethod
    def get_all_drives() -> List[DriveInfo]:
        """
        Obtém informações de todos os drives disponíveis.
        
        Returns:
            Lista de DriveInfo para todos os drives
        """
        drives = []
        
        try:
            if os.name == 'nt':  # Windows
                if win32api:
                    # Usa win32api para obter drives
                    drive_bits = win32api.GetLogicalDrives()
                    for i in range(26):
                        if drive_bits & (1 << i):
                            drive_letter = chr(ord('A') + i) + ':'
                            drive_info = DriveUtils.get_drive_info(drive_letter)
                            if drive_info:
                                drives.append(drive_info)
                else:
                    # Fallback: verifica drives comuns
                    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                        drive_path = letter + ':'
                        if os.path.exists(drive_path + '\\'):
                            drive_info = DriveUtils.get_drive_info(drive_path)
                            if drive_info:
                                drives.append(drive_info)
            else:
                # Para sistemas Unix-like
                if psutil:
                    for partition in psutil.disk_partitions():
                        drive_info = DriveUtils.get_drive_info(partition.mountpoint)
                        if drive_info:
                            drives.append(drive_info)
                else:
                    # Fallback básico
                    drive_info = DriveUtils.get_drive_info('/')
                    if drive_info:
                        drives.append(drive_info)

        except Exception as e:
            logging.error(f"Error getting all drives: {e}")

        return drives

    @staticmethod
    def check_drive_space(drive_path: str, required_space: int) -> SpaceCheckResult:
        """
        Verifica se há espaço suficiente no drive.
        
        Args:
            drive_path: Caminho do drive
            required_space: Espaço necessário em bytes
            
        Returns:
            SpaceCheckResult com resultado da verificação
        """
        try:
            drive_info = DriveUtils.get_drive_info(drive_path)
            if not drive_info:
                return SpaceCheckResult.create_failure(
                    0, required_space,
                    ["Drive não encontrado ou inacessível"]
                )

            available_space = drive_info.free_space

            if available_space >= required_space:
                return SpaceCheckResult.create_success(available_space, required_space)
            else:
                # Gera recomendações para liberar espaço
                recommendations = DriveUtils._generate_space_recommendations(
                    drive_info, required_space - available_space
                )
                return SpaceCheckResult.create_failure(
                    available_space, required_space, recommendations
                )

        except Exception as e:
            logging.error(f"Error checking drive space for {drive_path}: {e}")
            return SpaceCheckResult.create_failure(
                0, required_space,
                [f"Erro ao verificar espaço: {str(e)}"]
            )

    @staticmethod
    def _generate_space_recommendations(drive_info: DriveInfo, shortage: int) -> List[str]:
        """
        Gera recomendações para liberar espaço em disco.
        
        Args:
            drive_info: Informações do drive
            shortage: Quantidade de espaço em falta (bytes)
            
        Returns:
            Lista de recomendações
        """
        recommendations = []
        shortage_mb = shortage / (1024 * 1024)
        shortage_gb = shortage / (1024 * 1024 * 1024)

        recommendations.append(f"Libere pelo menos {shortage_mb:.1f} MB de espaço")
        
        if shortage_gb > 1:
            recommendations.append(f"Considere liberar {shortage_gb:.1f} GB para operação segura")

        recommendations.extend([
            "Execute a Limpeza de Disco do Windows",
            "Remova arquivos temporários e cache",
            "Desinstale programas não utilizados",
            "Mova arquivos grandes para outro local",
            "Esvazie a Lixeira"
        ])

        if drive_info.usage_percentage > 90:
            recommendations.append("Drive está quase cheio - considere usar outro drive")

        return recommendations

    @staticmethod
    def calculate_space_requirements(operation_type: str, data_size: int = 0) -> int:
        """
        Calcula requisitos de espaço para diferentes tipos de operação.
        
        Args:
            operation_type: Tipo de operação ("migration", "backup", "installation", etc.)
            data_size: Tamanho dos dados em bytes
            
        Returns:
            Espaço necessário em bytes
        """
        # Fatores de multiplicação para diferentes operações
        factors = {
            "migration": 1.5,  # 50% extra para arquivos temporários
            "backup": 1.1,    # 10% extra para metadados
            "installation": 2.0,  # 100% extra para descompressão e temporários
            "update": 1.3,    # 30% extra para backup da versão anterior
            "default": 1.2    # 20% extra por segurança
        }

        factor = factors.get(operation_type, factors["default"])
        required_space = int(data_size * factor)

        # Espaço mínimo de 100MB para qualquer operação
        min_space = 100 * 1024 * 1024  # 100MB
        return max(required_space, min_space)

    @staticmethod
    def validate_drive_for_selection(drive_path: str) -> DriveValidationResult:
        """
        Valida se um drive pode ser usado pela aplicação.
        
        Args:
            drive_path: Caminho do drive a validar
            
        Returns:
            DriveValidationResult com resultado da validação
        """
        issues = []
        warnings = []
        recommendations = []

        try:
            drive_info = DriveUtils.get_drive_info(drive_path)
            
            if not drive_info:
                issues.append("Drive não encontrado ou inacessível")
                return DriveValidationResult(
                    is_valid=False,
                    drive_path=drive_path,
                    issues=issues,
                    warnings=warnings,
                    recommendations=["Verifique se o drive está conectado e acessível"]
                )

            # Verifica tipo de drive
            if drive_info.drive_type == "network":
                warnings.append("Drive de rede pode ter performance reduzida")
                recommendations.append("Considere usar um drive local para melhor performance")

            if drive_info.drive_type == "removable":
                warnings.append("Drive removível pode ser desconectado")
                recommendations.append("Certifique-se de que o drive permanecerá conectado")

            # Verifica espaço disponível
            min_space = 1024 * 1024 * 1024  # 1GB mínimo
            if drive_info.free_space < min_space:
                issues.append(f"Espaço insuficiente (mínimo 1GB, disponível: {drive_info.free_space / (1024*1024*1024):.1f}GB)")

            # Verifica porcentagem de uso
            if drive_info.usage_percentage > 95:
                issues.append("Drive está quase cheio (>95% usado)")
            elif drive_info.usage_percentage > 85:
                warnings.append("Drive está com pouco espaço livre (<15%)")

            # Verifica sistema de arquivos
            if drive_info.file_system.upper() in ["FAT32", "FAT"]:
                warnings.append("Sistema de arquivos FAT32 tem limitações de tamanho de arquivo")
                recommendations.append("Considere usar um drive com NTFS para melhor compatibilidade")

            # Verifica permissões de escrita
            try:
                test_file = Path(drive_info.letter + "\\") / f"test_write_{int(time.time())}.tmp"
                test_file.touch()
                test_file.unlink()
            except Exception:
                issues.append("Sem permissão de escrita no drive")
                recommendations.append("Execute como administrador ou verifique permissões")

            is_valid = len(issues) == 0

            return DriveValidationResult(
                is_valid=is_valid,
                drive_path=drive_path,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )

        except Exception as e:
            logging.error(f"Error validating drive {drive_path}: {e}")
            return DriveValidationResult(
                is_valid=False,
                drive_path=drive_path,
                issues=[f"Erro na validação: {str(e)}"],
                warnings=[],
                recommendations=["Tente novamente ou escolha outro drive"]
            )

    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """
        Formata bytes em formato legível.
        
        Args:
            bytes_value: Valor em bytes
            
        Returns:
            String formatada (ex: "1.5 GB")
        """
        try:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        except Exception:
            return "0 B"

    @staticmethod
    def get_drive_health_status(drive_path: str) -> Dict[str, Any]:
        """
        Obtém status de saúde do drive (básico).
        
        Args:
            drive_path: Caminho do drive
            
        Returns:
            Dict com informações de saúde do drive
        """
        try:
            drive_info = DriveUtils.get_drive_info(drive_path)
            if not drive_info:
                return {"status": "unknown", "message": "Drive não encontrado"}

            # Status baseado em uso de espaço
            if drive_info.usage_percentage < 70:
                status = "healthy"
                message = "Drive com espaço adequado"
            elif drive_info.usage_percentage < 85:
                status = "warning"
                message = "Drive com espaço limitado"
            elif drive_info.usage_percentage < 95:
                status = "critical"
                message = "Drive quase cheio"
            else:
                status = "critical"
                message = "Drive crítico - espaço insuficiente"

            return {
                "status": status,
                "message": message,
                "usage_percentage": drive_info.usage_percentage,
                "free_space_gb": drive_info.free_space / (1024 * 1024 * 1024),
                "total_space_gb": drive_info.total_space / (1024 * 1024 * 1024)
            }

        except Exception as e:
            logging.error(f"Error getting drive health for {drive_path}: {e}")
            return {"status": "error", "message": f"Erro: {str(e)}"}