"""
Legacy Detection Service

Serviço responsável pela detecção obrigatória de instalações legadas do EmuDeck
e EmulationStationDE no drive C:, fornecendo informações para migração e limpeza.
"""

import logging
import os
import json
import winreg
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

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
    from sd_emulation_gui.utils.file_utils import FileUtils
except ImportError as e:
    logging.warning(f"Failed to import utilities: {e}")
    
    class BaseService:
        def __init__(self):
            pass

    class SystemUtils:
        @staticmethod
        def get_system_info():
            return {}
    
    class DriveUtils:
        @staticmethod
        def get_drive_info(drive):
            return {}
    
    class FileUtils:
        @staticmethod
        def exists(path: str) -> bool:
            import os
            return os.path.exists(path)
        
        @staticmethod
        def read_file(path: str) -> str:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ""

# Always define PathUtils locally to ensure it has the exists method
class PathUtils:
    @staticmethod
    def normalize_path(path: str) -> str:
        import os
        return os.path.normpath(path)
    
    @staticmethod
    def exists(path: str) -> bool:
        import os
        return os.path.exists(path)


class LegacyInstallation:
    """Representa uma instalação legada detectada."""
    
    def __init__(self, name: str, path: str, installation_type: str, 
                 version: str = "unknown", size_bytes: int = 0):
        """Inicializa informações da instalação legada.
        
        Args:
            name: Nome da instalação (EmuDeck, EmulationStationDE, etc.)
            path: Caminho da instalação
            installation_type: Tipo da instalação (emudeck, es-de, etc.)
            version: Versão detectada
            size_bytes: Tamanho da instalação em bytes
        """
        self.name = name
        self.path = PathUtils.normalize_path(path)
        self.installation_type = installation_type
        self.version = version
        self.size_bytes = size_bytes
        self.detected_at = datetime.now()
        self.components = []  # Lista de componentes detectados
        self.config_files = []  # Lista de arquivos de configuração
        self.data_directories = []  # Lista de diretórios de dados
        self.executables = []  # Lista de executáveis
        
    def add_component(self, component_path: str, component_type: str, 
                     description: str = "") -> None:
        """Adiciona um componente à instalação.
        
        Args:
            component_path: Caminho do componente
            component_type: Tipo do componente (config, data, executable, etc.)
            description: Descrição do componente
        """
        component = {
            'path': PathUtils.normalize_path(component_path),
            'type': component_type,
            'description': description,
            'exists': PathUtils.exists(component_path),
            'size_bytes': self._get_path_size(component_path) if PathUtils.exists(component_path) else 0
        }
        
        self.components.append(component)
        
        # Categorizar componente
        if component_type == 'config':
            self.config_files.append(component_path)
        elif component_type == 'data':
            self.data_directories.append(component_path)
        elif component_type == 'executable':
            self.executables.append(component_path)
    
    def _get_path_size(self, path: str) -> int:
        """Calcula o tamanho de um arquivo ou diretório."""
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)
            elif os.path.isdir(path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, IOError):
                            continue
                return total_size
        except Exception:
            pass
        return 0
    
    def calculate_total_size(self) -> int:
        """Calcula o tamanho total da instalação."""
        if self.size_bytes > 0:
            return self.size_bytes
        
        total_size = 0
        for component in self.components:
            total_size += component.get('size_bytes', 0)
        
        self.size_bytes = total_size
        return total_size
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte a instalação para dicionário."""
        return {
            'name': self.name,
            'path': self.path,
            'installation_type': self.installation_type,
            'version': self.version,
            'size_bytes': self.size_bytes,
            'size_formatted': DriveUtils.format_bytes(self.size_bytes),
            'detected_at': self.detected_at.isoformat(),
            'components_count': len(self.components),
            'config_files_count': len(self.config_files),
            'data_directories_count': len(self.data_directories),
            'executables_count': len(self.executables),
            'components': self.components,
            'config_files': self.config_files,
            'data_directories': self.data_directories,
            'executables': self.executables
        }


class LegacyDetectionService(BaseService):
    """Serviço para detecção de instalações legadas."""
    
    def __init__(self, base_path: str = None):
        """Inicializa o serviço de detecção de instalações legadas.
        
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
        
        # Cache de detecções
        self._detected_installations = {}
        self._last_scan_time = None
        self._scan_in_progress = False
        
        # Configurações de detecção
        self.available_drives = self._get_available_drives()  # Detecta drives disponíveis
        self.scan_timeout_seconds = 300  # Timeout de 5 minutos para scan
        
        # Padrões de detecção para EmuDeck (sem limitação de drive)
        self.emudeck_patterns = {
            'installation_paths': [
                '{drive}\\EmuDeck',
                '{drive}\\Emulation',
                '{drive}\\Games\\EmuDeck',
                '{drive}\\Program Files\\EmuDeck',
                '{drive}\\Program Files (x86)\\EmuDeck',
                '{drive}\\Users\\{username}\\EmuDeck',
                '{drive}\\Users\\{username}\\AppData\\Local\\EmuDeck',
                '{drive}\\Users\\{username}\\AppData\\Roaming\\EmuDeck'
            ],
            'config_files': [
                'emudeck.cfg',
                'emudeck.json',
                'config.json',
                'settings.ini'
            ],
            'executables': [
                'EmuDeck.exe',
                'emudeck.exe',
                'EmuDeck-installer.exe'
            ],
            'data_directories': [
                'roms',
                'saves',
                'states',
                'bios',
                'tools',
                'emulators'
            ]
        }
        
        # Padrões de detecção para EmulationStationDE (sem limitação de drive)
        self.es_de_patterns = {
            'installation_paths': [
                '{drive}\\EmulationStation-DE',
                '{drive}\\ES-DE',
                '{drive}\\Emulation\\EmulationStation-DE',
                '{drive}\\Program Files\\EmulationStation-DE',
                '{drive}\\Program Files (x86)\\EmulationStation-DE',
                '{drive}\\Users\\{username}\\EmulationStation-DE',
                '{drive}\\Users\\{username}\\AppData\\Local\\EmulationStation-DE',
                '{drive}\\Users\\{username}\\AppData\\Roaming\\EmulationStation-DE'
            ],
            'config_files': [
                'es_settings.xml',
                'es_systems.xml',
                'es_input.xml',
                'es_find_rules.xml',  # Arquivo crítico para resolução de caminhos
                'collections.xml'
            ],
            'executables': [
                'EmulationStation.exe',
                'ES-DE.exe',
                'emulationstation.exe'
            ],
            'data_directories': [
                'roms',
                'downloaded_media',
                'gamelists',
                'themes',
                'custom_systems'
            ]
        }
        
        # Nível 1: Runtimes e Pré-requisitos do Sistema
        self.level1_system_runtimes = {
            'visual_cpp_redistributables': {
                'registry_keys': [
                    r'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
                    r'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x86',
                    r'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
                    r'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x86',
                    r'SOFTWARE\Classes\Installer\Products'  # Para versões mais antigas
                ],
                'display_names': [
                    'Microsoft Visual C++ 2015-2022 Redistributable',
                    'Microsoft Visual C++ 2019 Redistributable',
                    'Microsoft Visual C++ 2017 Redistributable',
                    'Microsoft Visual C++ 2015 Redistributable',
                    'Microsoft Visual C++ 2013 Redistributable',
                    'Microsoft Visual C++ 2012 Redistributable',
                    'Microsoft Visual C++ 2010 Redistributable',
                    'Microsoft Visual C++ 2008 Redistributable',
                    'Microsoft Visual C++ 2005 Redistributable'
                ]
            },
            'dotnet_framework': {
                'registry_keys': [
                    r'SOFTWARE\Microsoft\NET Framework Setup\NDP',
                    r'SOFTWARE\WOW6432Node\Microsoft\NET Framework Setup\NDP',
                    r'SOFTWARE\dotnet\Setup\InstalledVersions'
                ],
                'display_names': [
                    '.NET Framework',
                    '.NET Core',
                    '.NET 5.0',
                    '.NET 6.0',
                    '.NET 7.0',
                    '.NET 8.0'
                ]
            },
            'directx_runtime': {
                'registry_keys': [
                    r'SOFTWARE\Microsoft\DirectX',
                    r'SOFTWARE\WOW6432Node\Microsoft\DirectX'
                ],
                'files': [
                    'C:\\Windows\\System32\\d3d11.dll',
                    'C:\\Windows\\System32\\dxgi.dll',
                    'C:\\Windows\\System32\\d3d9.dll',
                    'C:\\Windows\\SysWOW64\\d3d11.dll',
                    'C:\\Windows\\SysWOW64\\dxgi.dll',
                    'C:\\Windows\\SysWOW64\\d3d9.dll'
                ]
            }
        }
        
        # Nível 2: Dependências da Ferramenta de Gerenciamento EmuDeck
        self.level2_emudeck_dependencies = {
            'git': {
                'registry_keys': [
                    r'SOFTWARE\GitForWindows',
                    r'SOFTWARE\WOW6432Node\GitForWindows'
                ],
                'executables': [
                    'git.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\Git\\bin\\git.exe',
                    'C:\\Program Files (x86)\\Git\\bin\\git.exe',
                    'C:\\Git\\bin\\git.exe'
                ]
            },
            '7zip': {
                'registry_keys': [
                    r'SOFTWARE\7-Zip',
                    r'SOFTWARE\WOW6432Node\7-Zip'
                ],
                'executables': [
                    '7z.exe',
                    '7za.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\7-Zip\\7z.exe',
                    'C:\\Program Files (x86)\\7-Zip\\7z.exe'
                ]
            },
            'powershell_core': {
                'registry_keys': [
                    r'SOFTWARE\Microsoft\PowerShellCore',
                    r'SOFTWARE\WOW6432Node\Microsoft\PowerShellCore'
                ],
                'executables': [
                    'pwsh.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\PowerShell\\7\\pwsh.exe',
                    'C:\\Program Files (x86)\\PowerShell\\7\\pwsh.exe'
                ]
            }
        }
        
        # Nível 3: Dependências de Frontend e Backend
        self.level3_frontend_backend = {
            'steam': {
                'registry_keys': [
                    r'SOFTWARE\Valve\Steam',
                    r'SOFTWARE\WOW6432Node\Valve\Steam'
                ],
                'executables': [
                    'steam.exe'
                ],
                'common_paths': [
                    'C:\\Program Files (x86)\\Steam\\steam.exe',
                    'C:\\Program Files\\Steam\\steam.exe'
                ],
                'config_files': [
                    'config\\config.vdf',
                    'userdata'
                ]
            },
            'sdl2': {
                'dll_files': [
                    'SDL2.dll',
                    'SDL2_image.dll',
                    'SDL2_mixer.dll',
                    'SDL2_ttf.dll'
                ],
                'common_paths': [
                    'C:\\Windows\\System32',
                    'C:\\Windows\\SysWOW64'
                ]
            },
            'boost_cpp': {
                'dll_files': [
                    'boost_filesystem*.dll',
                    'boost_locale*.dll',
                    'boost_system*.dll'
                ],
                'registry_keys': [
                    r'SOFTWARE\boost.org'
                ]
            },
            'curl': {
                'dll_files': [
                    'libcurl.dll',
                    'curl.dll'
                ],
                'executables': [
                    'curl.exe'
                ]
            },
            'freeimage': {
                'dll_files': [
                    'FreeImage.dll',
                    'FreeImagePlus.dll'
                ]
            },
            'freetype': {
                'dll_files': [
                    'freetype.dll',
                    'freetype6.dll'
                ]
            },
            'eigen': {
                'header_files': [
                    'Eigen\\Dense',
                    'Eigen\\Core'
                ]
            },
            'vlc': {
                'registry_keys': [
                    r'SOFTWARE\VideoLAN\VLC',
                    r'SOFTWARE\WOW6432Node\VideoLAN\VLC'
                ],
                'dll_files': [
                    'libvlc.dll',
                    'libvlccore.dll'
                ],
                'common_paths': [
                    'C:\\Program Files\\VideoLAN\\VLC',
                    'C:\\Program Files (x86)\\VideoLAN\\VLC'
                ]
            }
        }
        
        # Nível 4: Dependências Específicas do Emulador
        self.level4_emulator_dependencies = {
            'retroarch': {
                'registry_keys': [
                    r'SOFTWARE\RetroArch',
                    r'SOFTWARE\WOW6432Node\RetroArch'
                ],
                'executables': [
                    'retroarch.exe'
                ],
                'common_paths': [
                    'C:\\RetroArch\\retroarch.exe',
                    'C:\\Program Files\\RetroArch\\retroarch.exe',
                    'C:\\Program Files (x86)\\RetroArch\\retroarch.exe'
                ],
                'config_files': [
                    'retroarch.cfg'
                ]
            },
            'pcsx2': {
                'executables': [
                    'pcsx2.exe',
                    'PCSX2.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\PCSX2\\pcsx2.exe',
                    'C:\\Program Files (x86)\\PCSX2\\pcsx2.exe',
                    'C:\\PCSX2\\pcsx2.exe'
                ]
            },
            'dolphin': {
                'executables': [
                    'Dolphin.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\Dolphin-x64\\Dolphin.exe',
                    'C:\\Program Files (x86)\\Dolphin-x64\\Dolphin.exe',
                    'C:\\Dolphin\\Dolphin.exe'
                ]
            },
            'rpcs3': {
                'executables': [
                    'rpcs3.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\RPCS3\\rpcs3.exe',
                    'C:\\Program Files (x86)\\RPCS3\\rpcs3.exe',
                    'C:\\RPCS3\\rpcs3.exe'
                ]
            },
            'cemu': {
                'executables': [
                    'Cemu.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\Cemu\\Cemu.exe',
                    'C:\\Program Files (x86)\\Cemu\\Cemu.exe',
                    'C:\\Cemu\\Cemu.exe'
                ]
            },
            'yuzu': {
                'executables': [
                    'yuzu.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\yuzu\\yuzu.exe',
                    'C:\\Program Files (x86)\\yuzu\\yuzu.exe',
                    'C:\\yuzu\\yuzu.exe'
                ]
            },
            'ryujinx': {
                'executables': [
                    'Ryujinx.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\Ryujinx\\Ryujinx.exe',
                    'C:\\Program Files (x86)\\Ryujinx\\Ryujinx.exe',
                    'C:\\Ryujinx\\Ryujinx.exe'
                ]
            },
            'mame': {
                'executables': [
                    'mame.exe',
                    'mame64.exe'
                ],
                'common_paths': [
                    'C:\\Program Files\\MAME\\mame.exe',
                    'C:\\Program Files (x86)\\MAME\\mame.exe',
                    'C:\\MAME\\mame.exe'
                ]
            }
        }
    
    def _get_available_drives(self) -> List[str]:
        """Detecta todos os drives disponíveis no sistema.
        
        Returns:
            Lista de drives disponíveis (ex: ['C:', 'D:', 'E:'])
        """
        drives = []
        try:
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:"
                if os.path.exists(drive + "\\"):
                    drives.append(drive)
            
            self.logger.debug(f"Drives disponíveis detectados: {drives}")
            return drives
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar drives disponíveis: {e}")
            return ['C:']  # Fallback para drive C: apenas

    def initialize(self) -> None:
        """Inicializa o LegacyDetectionService."""
        try:
            self.logger.info("Inicializando LegacyDetectionService...")
            
            # Garantir que os atributos existam
            if not hasattr(self, 'available_drives'):
                self.available_drives = self._get_available_drives()
            if not hasattr(self, '_detected_installations'):
                self._detected_installations = {}
            if not hasattr(self, '_last_scan_time'):
                self._last_scan_time = None
            if not hasattr(self, '_scan_in_progress'):
                self._scan_in_progress = False
            
            # Garantir que os padrões de detecção existam
            if not hasattr(self, 'emudeck_patterns'):
                self.emudeck_patterns = {
                    'installation_paths': [
                        'C:\\EmuDeck',
                        'C:\\Program Files\\EmuDeck',
                        'C:\\Program Files (x86)\\EmuDeck',
                        'C:\\Users\\{username}\\EmuDeck',
                        'C:\\Users\\{username}\\AppData\\Local\\EmuDeck',
                        'C:\\Users\\{username}\\AppData\\Roaming\\EmuDeck'
                    ],
                    'config_files': [
                        'emudeck.cfg',
                        'emudeck.json',
                        'config.json',
                        'settings.ini'
                    ],
                    'executables': [
                        'EmuDeck.exe',
                        'emudeck.exe',
                        'EmuDeck-installer.exe'
                    ],
                    'data_directories': [
                        'roms',
                        'saves',
                        'states',
                        'bios',
                        'tools',
                        'emulators'
                    ]
                }
            
            if not hasattr(self, 'es_de_patterns'):
                self.es_de_patterns = {
                    'installation_paths': [
                        'C:\\EmulationStation-DE',
                        'C:\\Program Files\\EmulationStation-DE',
                        'C:\\Program Files (x86)\\EmulationStation-DE',
                        'C:\\Users\\{username}\\EmulationStation-DE',
                        'C:\\Users\\{username}\\AppData\\Local\\EmulationStation-DE',
                        'C:\\Users\\{username}\\AppData\\Roaming\\EmulationStation-DE',
                        'C:\\ES-DE'
                    ],
                    'config_files': [
                        'es_settings.xml',
                        'es_systems.xml',
                        'es_input.xml',
                        'collections.xml'
                    ],
                    'executables': [
                        'EmulationStation.exe',
                        'ES-DE.exe',
                        'emulationstation.exe'
                    ],
                    'data_directories': [
                        'roms',
                        'downloaded_media',
                        'gamelists',
                        'themes',
                        'custom_systems'
                    ]
                }
            
            # Verificar se há drives disponíveis
            if not self.available_drives:
                self.logger.warning("Nenhum drive disponível detectado")
            else:
                self.logger.info(f"Drives disponíveis detectados: {self.available_drives}")
            
            # Não executar scan inicial durante inicialização para evitar erros
            # O scan será executado quando necessário via chamadas explícitas
            self.logger.debug("Inicialização concluída. Scan será executado quando solicitado.")
            
            self.logger.info("LegacyDetectionService inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar LegacyDetectionService: {e}")
            # Não fazer raise para permitir que o container continue funcionando
            # Definir valores padrão em caso de erro
            if not hasattr(self, 'available_drives'):
                self.available_drives = ['C:']
            if not hasattr(self, '_detected_installations'):
                self._detected_installations = {}
            if not hasattr(self, '_last_scan_time'):
                self._last_scan_time = None
            if not hasattr(self, '_scan_in_progress'):
                self._scan_in_progress = False
    
    def _verify_available_drives(self) -> bool:
        """Verifica se há drives disponíveis para scan."""
        try:
            for drive in self.available_drives:
                drive_info = DriveUtils.get_drive_info(drive)
                if drive_info and drive_info.total_space > 0:
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Erro ao verificar drives disponíveis: {e}")
            return False
    
    def _expand_path_patterns(self, patterns: List[str]) -> List[str]:
        """Expande padrões de caminho com variáveis do sistema e múltiplos drives."""
        expanded_paths = []
        
        try:
            # Obter nome de usuário atual
            username = os.getenv('USERNAME', 'User')
            
            for pattern in patterns:
                # Se o padrão contém {drive}, expandir para todos os drives disponíveis
                if '{drive}' in pattern:
                    for drive in self.available_drives:
                        expanded_path = pattern.replace('{drive}', drive)
                        expanded_path = expanded_path.replace('{username}', username)
                        expanded_paths.append(expanded_path)
                else:
                    # Substituir apenas variáveis de usuário
                    expanded_path = pattern.replace('{username}', username)
                    expanded_paths.append(expanded_path)
                
        except Exception as e:
            self.logger.error(f"Erro ao expandir padrões de caminho: {e}")
        
        return expanded_paths
    
    def _detect_emudeck_installation(self) -> Optional[LegacyInstallation]:
        """Detecta instalação do EmuDeck."""
        try:
            self.logger.debug("Procurando instalação do EmuDeck...")
            
            # Expandir padrões de caminho
            installation_paths = self._expand_path_patterns(self.emudeck_patterns['installation_paths'])
            
            # Procurar por diretórios de instalação
            for install_path in installation_paths:
                if not PathUtils.exists(install_path):
                    continue
                
                self.logger.debug(f"Encontrado diretório EmuDeck: {install_path}")
                
                # Criar objeto de instalação
                installation = LegacyInstallation(
                    name="EmuDeck",
                    path=install_path,
                    installation_type="emudeck"
                )
                
                # Detectar versão
                version = self._detect_emudeck_version(install_path)
                installation.version = version
                
                # Procurar componentes
                self._scan_emudeck_components(installation, install_path)
                
                # Calcular tamanho total
                installation.calculate_total_size()
                
                self.logger.info(f"EmuDeck detectado em: {install_path} (versão: {version})")
                return installation
            
            self.logger.debug("Nenhuma instalação do EmuDeck encontrada")
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar EmuDeck: {e}")
            return None
    
    def _detect_emudeck_version(self, install_path: str) -> str:
        """Detecta a versão do EmuDeck instalado."""
        try:
            # Procurar por arquivos de configuração com informações de versão
            config_files = ['emudeck.json', 'config.json', 'version.txt']
            
            for config_file in config_files:
                config_path = os.path.join(install_path, config_file)
                if not PathUtils.exists(config_path):
                    continue
                
                try:
                    content = FileUtils.read_file(config_path)
                    
                    if config_file.endswith('.json'):
                        # Tentar parsear JSON
                        data = json.loads(content)
                        version = data.get('version', data.get('emudeck_version', 'unknown'))
                        if version != 'unknown':
                            return version
                    else:
                        # Arquivo de texto simples
                        lines = content.strip().split('\n')
                        if lines:
                            return lines[0].strip()
                            
                except Exception:
                    continue
            
            # Fallback: tentar detectar pela presença de executáveis
            for executable in self.emudeck_patterns['executables']:
                exe_path = os.path.join(install_path, executable)
                if PathUtils.exists(exe_path):
                    return "detected"
            
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar versão do EmuDeck: {e}")
            return "unknown"
    
    def _scan_emudeck_components(self, installation: LegacyInstallation, install_path: str) -> None:
        """Escaneia componentes da instalação do EmuDeck."""
        try:
            # Procurar executáveis
            for executable in self.emudeck_patterns['executables']:
                exe_path = os.path.join(install_path, executable)
                if PathUtils.exists(exe_path):
                    installation.add_component(
                        exe_path, 'executable', 
                        f'Executável principal do EmuDeck: {executable}'
                    )
            
            # Procurar arquivos de configuração
            for config_file in self.emudeck_patterns['config_files']:
                config_path = os.path.join(install_path, config_file)
                if PathUtils.exists(config_path):
                    installation.add_component(
                        config_path, 'config',
                        f'Arquivo de configuração: {config_file}'
                    )
            
            # Procurar diretórios de dados
            for data_dir in self.emudeck_patterns['data_directories']:
                data_path = os.path.join(install_path, data_dir)
                if PathUtils.exists(data_path):
                    installation.add_component(
                        data_path, 'data',
                        f'Diretório de dados: {data_dir}'
                    )
            
            # Escanear subdiretórios para componentes adicionais
            try:
                for item in os.listdir(install_path):
                    item_path = os.path.join(install_path, item)
                    
                    if os.path.isdir(item_path):
                        # Verificar se é um diretório importante
                        if item.lower() in ['tools', 'emulators', 'configs']:
                            installation.add_component(
                                item_path, 'data',
                                f'Diretório do sistema: {item}'
                            )
                    elif os.path.isfile(item_path):
                        # Verificar se é um arquivo importante
                        if item.lower().endswith(('.cfg', '.ini', '.xml', '.json')):
                            installation.add_component(
                                item_path, 'config',
                                f'Arquivo de configuração: {item}'
                            )
                            
            except Exception as e:
                self.logger.warning(f"Erro ao escanear subdiretórios do EmuDeck: {e}")
                
        except Exception as e:
            self.logger.error(f"Erro ao escanear componentes do EmuDeck: {e}")

    def _check_registry_key(self, key_path: str, hive=winreg.HKEY_LOCAL_MACHINE) -> bool:
        """Verifica se uma chave do registro existe.
        
        Args:
            key_path: Caminho da chave no registro
            hive: Hive do registro (padrão: HKEY_LOCAL_MACHINE)
            
        Returns:
            True se a chave existe, False caso contrário
        """
        try:
            with winreg.OpenKey(hive, key_path):
                return True
        except (FileNotFoundError, OSError):
            return False

    def _get_registry_value(self, key_path: str, value_name: str, hive=winreg.HKEY_LOCAL_MACHINE) -> Optional[str]:
        """Obtém valor de uma chave do registro.
        
        Args:
            key_path: Caminho da chave no registro
            value_name: Nome do valor
            hive: Hive do registro
            
        Returns:
            Valor da chave ou None se não encontrado
        """
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return str(value)
        except (FileNotFoundError, OSError):
            return None

    def _find_executable_in_path(self, executable_name: str) -> Optional[str]:
        """Procura um executável no PATH do sistema.
        
        Args:
            executable_name: Nome do executável
            
        Returns:
            Caminho completo do executável ou None se não encontrado
        """
        try:
            result = subprocess.run(['where', executable_name], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        return None

    def _find_dll_in_system(self, dll_name: str) -> List[str]:
        """Procura uma DLL específica em locais comuns do sistema.
        
        Args:
            dll_name: Nome da DLL a procurar
            
        Returns:
            Lista de caminhos onde a DLL foi encontrada
        """
        found_paths = []
        
        # Locais comuns para procurar DLLs
        search_paths = [
            os.environ.get('SYSTEMROOT', 'C:\\Windows') + '\\System32',
            os.environ.get('SYSTEMROOT', 'C:\\Windows') + '\\SysWOW64',
            os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
            os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
            os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
            'C:\\Windows\\System32',
            'C:\\Windows\\SysWOW64'
        ]
        
        # Adicionar PATH do sistema
        path_env = os.environ.get('PATH', '')
        if path_env:
            search_paths.extend(path_env.split(os.pathsep))
        
        for search_path in search_paths:
            if not search_path or not os.path.exists(search_path):
                continue
                
            dll_path = os.path.join(search_path, dll_name)
            if os.path.isfile(dll_path):
                found_paths.append(dll_path)
        
        return found_paths

    def _validate_component_integrity(self, component: Dict[str, Any]) -> bool:
        """Valida a integridade de um componente detectado.
        
        Args:
            component: Dicionário com informações do componente
            
        Returns:
            True se o componente está íntegro, False caso contrário
        """
        try:
            # Verificar se o caminho principal existe
            if 'path' in component and component['path']:
                if not os.path.exists(component['path']):
                    return False
            
            # Verificar arquivos específicos se listados
            if 'files' in component:
                for file_path in component['files']:
                    if not os.path.isfile(file_path):
                        return False
            
            # Verificar chaves de registro se especificadas
            if 'registry' in component and component['registry']:
                if not self._check_registry_key(component['registry']):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Erro ao validar integridade do componente {component.get('name', 'unknown')}: {e}")
            return False

    def _get_component_version(self, component: Dict[str, Any]) -> str:
        """Tenta obter a versão de um componente.
        
        Args:
            component: Dicionário com informações do componente
            
        Returns:
            String com a versão ou 'unknown'
        """
        try:
            # Tentar obter versão do registro
            if 'registry' in component and component['registry']:
                version = self._get_registry_value(component['registry'], 'Version')
                if not version:
                    version = self._get_registry_value(component['registry'], 'DisplayVersion')
                if version:
                    return version
            
            # Tentar obter versão de arquivo executável
            if 'path' in component and component['path']:
                if os.path.isfile(component['path']) and component['path'].endswith('.exe'):
                    try:
                        import win32api
                        info = win32api.GetFileVersionInfo(component['path'], "\\")
                        ms = info['FileVersionMS']
                        ls = info['FileVersionLS']
                        version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
                        return version
                    except ImportError:
                        pass  # win32api não disponível
                    except Exception:
                        pass  # Erro ao obter versão
            
            return 'unknown'
            
        except Exception:
            return 'unknown'

    def _create_hierarchical_installation(self, name: str, level: int, components: List[Dict[str, Any]]) -> LegacyInstallation:
        """Cria um objeto LegacyInstallation para componentes hierárquicos.
        
        Args:
            name: Nome da categoria de instalação
            level: Nível hierárquico (1-4)
            components: Lista de componentes detectados
            
        Returns:
            Objeto LegacyInstallation configurado
        """
        # Calcular tamanho total estimado baseado no número de componentes
        estimated_size = len(components) * 50 * 1024 * 1024  # 50MB por componente (estimativa)
        
        # Criar path virtual para múltiplos componentes
        paths = []
        for component in components:
            if 'path' in component:
                paths.append(component['path'])
            elif 'files' in component:
                paths.extend(component['files'])
        
        primary_path = paths[0] if paths else f"Sistema (Nível {level})"
        
        installation = LegacyInstallation(
            name=name,
            path=primary_path,
            installation_type=f"level{level}_components",
            version=f"{len(components)} componentes",
            size_bytes=estimated_size
        )
        
        # Adicionar componentes como metadados
        installation.components = components
        installation.level = level
        installation.component_count = len(components)
        
        return installation

    def validate_system_integrity(self) -> Dict[str, Any]:
        """Valida a integridade geral do sistema EmuDeck detectado.
        
        Returns:
            Dicionário com resultados da validação
        """
        validation_results = {
            'overall_status': 'unknown',
            'critical_missing': [],
            'warnings': [],
            'recommendations': [],
            'component_status': {}
        }
        
        try:
            # Verificar se há instalações detectadas
            if not self._detected_installations:
                validation_results['overall_status'] = 'no_installations'
                validation_results['recommendations'].append(
                    'Nenhuma instalação EmuDeck detectada. Execute um scan primeiro.'
                )
                return validation_results
            
            # Verificar componentes críticos
            critical_components = ['steam']  # Steam é obrigatório
            missing_critical = []
            
            for installation_type, installation in self._detected_installations.items():
                if hasattr(installation, 'components'):
                    for component in installation.components:
                        component_name = component.get('name', '').lower()
                        
                        # Verificar integridade do componente
                        is_valid = self._validate_component_integrity(component)
                        validation_results['component_status'][component.get('name', 'unknown')] = {
                            'valid': is_valid,
                            'path': component.get('path'),
                            'critical': component.get('critical', False)
                        }
                        
                        # Verificar se é componente crítico
                        if any(critical in component_name for critical in critical_components):
                            if not is_valid:
                                missing_critical.append(component.get('name'))
            
            # Determinar status geral
            if missing_critical:
                validation_results['overall_status'] = 'critical_issues'
                validation_results['critical_missing'] = missing_critical
            else:
                validation_results['overall_status'] = 'healthy'
            
            # Executar validações de robustez adicionais
            robustness_results = self._perform_robustness_validations()
            validation_results['robustness_validations'] = robustness_results
            
            # Atualizar status baseado nas validações de robustez
            if robustness_results.get('critical_failures', 0) > 0:
                if validation_results['overall_status'] == 'healthy':
                    validation_results['overall_status'] = 'robustness_issues'
                validation_results['warnings'].extend(robustness_results.get('warnings', []))
            
            # Adicionar recomendações baseadas no status
            if validation_results['overall_status'] == 'critical_issues':
                validation_results['recommendations'].append(
                    'Componentes críticos estão faltando ou corrompidos. '
                    'Reinstale o EmuDeck ou os componentes específicos.'
                )
            elif validation_results['overall_status'] == 'robustness_issues':
                validation_results['recommendations'].append(
                    'Sistema EmuDeck detectado, mas há problemas de robustez na estrutura. '
                    'Verifique a integridade dos caminhos relativos e estrutura bifurcada.'
                )
                validation_results['recommendations'].extend(robustness_results.get('recommendations', []))
            elif validation_results['overall_status'] == 'healthy':
                validation_results['recommendations'].append(
                    'Sistema EmuDeck parece estar funcionando corretamente.'
                )
            
        except Exception as e:
            self.logger.error(f"Erro durante validação de integridade: {e}")
            validation_results['overall_status'] = 'error'
            validation_results['warnings'].append(f"Erro durante validação: {str(e)}")
        
        return validation_results
    
    def _perform_robustness_validations(self) -> Dict[str, Any]:
        """Executa validações de robustez do sistema EmuDeck.
        
        Returns:
            Dict com resultados das validações de robustez
        """
        robustness_results = {
            'es_de_path_validation': {},
            'bifurcated_structure_validation': {},
            'emulator_path_resolution': {},
            'critical_failures': 0,
            'warnings': [],
            'recommendations': []
        }
        
        try:
            # Encontrar instalações ES-DE e EmuDeck
            es_de_installation = None
            emudeck_installation = None
            
            for installation_type, installation in self._detected_installations.items():
                if 'es-de' in installation_type.lower() or 'emulationstation' in installation_type.lower():
                    es_de_installation = installation
                elif 'emudeck' in installation_type.lower():
                    emudeck_installation = installation
            
            # Validação 1: ES-DE Path Resolution
            if es_de_installation:
                self.logger.debug(f"Validando resolução de caminhos ES-DE: {es_de_installation.path}")
                es_validation = self._validate_es_de_path_resolution(es_de_installation.path)
                robustness_results['es_de_path_validation'] = es_validation
                
                if es_validation['validation_status'] == 'failed':
                    robustness_results['critical_failures'] += 1
                    robustness_results['warnings'].append(
                        f"Falha na validação de caminhos ES-DE: {es_de_installation.path}"
                    )
                    robustness_results['recommendations'].append(
                        "Verificar se es_find_rules.xml existe e contém configurações válidas"
                    )
                elif es_validation['validation_status'] == 'partial':
                    robustness_results['warnings'].append(
                        "Validação parcial de caminhos ES-DE - alguns caminhos podem não funcionar"
                    )
            else:
                robustness_results['warnings'].append("ES-DE não detectado - pulando validação de caminhos")
            
            # Validação 2: Estrutura Bifurcada
            if emudeck_installation and es_de_installation:
                # Tentar encontrar AppData do EmuDeck
                username = os.getenv('USERNAME', 'User')
                appdata_paths = [
                    f"C:\\Users\\{username}\\AppData\\Local\\EmuDeck",
                    f"C:\\Users\\{username}\\AppData\\Roaming\\EmuDeck"
                ]
                
                appdata_path = None
                for path in appdata_paths:
                    if PathUtils.exists(path):
                        appdata_path = path
                        break
                
                if appdata_path:
                    self.logger.debug(f"Validando estrutura bifurcada: {emudeck_installation.path} <-> {appdata_path}")
                    bifurcated_validation = self._validate_bifurcated_structure(
                        emudeck_installation.path, appdata_path
                    )
                    robustness_results['bifurcated_structure_validation'] = bifurcated_validation
                    
                    if bifurcated_validation['validation_status'] == 'failed':
                        robustness_results['critical_failures'] += 1
                        robustness_results['warnings'].append(
                            "Estrutura bifurcada EmuDeck não está consistente"
                        )
                        robustness_results['recommendations'].append(
                            "Verificar se configurações no AppData referenciam corretamente o diretório Emulation"
                        )
                else:
                    robustness_results['warnings'].append(
                        "AppData do EmuDeck não encontrado - pulando validação de estrutura bifurcada"
                    )
            
            # Validação 3: Resolução de Caminhos de Emuladores
            if es_de_installation:
                self.logger.debug(f"Testando resolução de caminhos de emuladores: {es_de_installation.path}")
                emulator_validation = self._test_emulator_path_resolution(es_de_installation.path)
                robustness_results['emulator_path_resolution'] = emulator_validation
                
                if emulator_validation['validation_status'] == 'failed':
                    robustness_results['warnings'].append(
                        "Nenhum emulador encontrado via caminhos relativos"
                    )
                    robustness_results['recommendations'].append(
                        "Verificar se emuladores estão instalados nos caminhos esperados relativos ao ES-DE"
                    )
                elif emulator_validation['validation_status'] == 'partial':
                    success_rate = (emulator_validation['successful_tests'] / 
                                  emulator_validation['total_tests'] * 100)
                    robustness_results['warnings'].append(
                        f"Resolução parcial de emuladores ({success_rate:.1f}% encontrados)"
                    )
            
        except Exception as e:
            self.logger.error(f"Erro durante validações de robustez: {e}")
            robustness_results['critical_failures'] += 1
            robustness_results['warnings'].append(f"Erro durante validações: {str(e)}")
        
        return robustness_results

    def _find_dll_in_system(self, dll_name: str) -> List[str]:
        """Procura por uma DLL específica nos diretórios do sistema.
        
        Args:
            dll_name: Nome da DLL a procurar (pode incluir wildcards como *)
            
        Returns:
            Lista de caminhos onde a DLL foi encontrada
        """
        found_paths = []
        
        # Diretórios padrão do sistema para procurar DLLs
        system_dirs = [
            'C:\\Windows\\System32',
            'C:\\Windows\\SysWOW64',
            'C:\\Windows\\System',
            'C:\\Program Files\\Common Files',
            'C:\\Program Files (x86)\\Common Files'
        ]
        
        try:
            import glob
            
            for system_dir in system_dirs:
                if not PathUtils.exists(system_dir):
                    continue
                    
                # Procurar pela DLL usando glob para suportar wildcards
                search_pattern = os.path.join(system_dir, dll_name)
                matches = glob.glob(search_pattern)
                
                for match in matches:
                    if PathUtils.exists(match):
                        found_paths.append(match)
                        
        except Exception as e:
            self.logger.debug(f"Erro ao procurar DLL {dll_name}: {e}")
            
        return found_paths

    def _find_executable_in_path(self, exe_name: str) -> Optional[str]:
        """Procura por um executável no PATH do sistema.
        
        Args:
            exe_name: Nome do executável a procurar
            
        Returns:
            Caminho completo do executável se encontrado, None caso contrário
        """
        try:
            import shutil
            exe_path = shutil.which(exe_name)
            return exe_path if exe_path and PathUtils.exists(exe_path) else None
        except Exception as e:
            self.logger.debug(f"Erro ao procurar executável {exe_name}: {e}")
            return None

    def _check_registry_key(self, registry_path: str, hive: int = winreg.HKEY_LOCAL_MACHINE) -> bool:
        """Verifica se uma chave do registro existe.
        
        Args:
            registry_path: Caminho da chave no registro
            hive: Hive do registro (padrão: HKEY_LOCAL_MACHINE)
            
        Returns:
            True se a chave existe, False caso contrário
        """
        try:
            with winreg.OpenKey(hive, registry_path):
                return True
        except (FileNotFoundError, OSError, PermissionError):
            return False

    def _get_registry_value(self, registry_path: str, value_name: str, hive: int = winreg.HKEY_LOCAL_MACHINE) -> Optional[str]:
        """Obtém um valor específico do registro.
        
        Args:
            registry_path: Caminho da chave no registro
            value_name: Nome do valor a obter
            hive: Hive do registro (padrão: HKEY_LOCAL_MACHINE)
            
        Returns:
            Valor do registro se encontrado, None caso contrário
        """
        try:
            with winreg.OpenKey(hive, registry_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return str(value)
        except (FileNotFoundError, OSError, PermissionError):
            return None

    def _detect_dll_component(self, component_name: str, dll_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detecta um componente baseado em DLLs específicas.
        
        Args:
            component_name: Nome do componente
            dll_config: Configuração de DLLs para o componente
            
        Returns:
            Informações do componente se detectado, None caso contrário
        """
        component_info = {
            'name': component_name,
            'status': 'not_found',
            'files': [],
            'paths': []
        }
        
        try:
            # Procurar por DLLs específicas
            if 'dll_files' in dll_config:
                for dll_name in dll_config['dll_files']:
                    found_paths = self._find_dll_in_system(dll_name)
                    if found_paths:
                        component_info['files'].extend(found_paths)
                        component_info['paths'].extend(found_paths)
                        component_info['status'] = 'installed'
            
            # Verificar caminhos comuns se especificados
            if 'common_paths' in dll_config:
                for path in dll_config['common_paths']:
                    if PathUtils.exists(path):
                        component_info['paths'].append(path)
                        component_info['status'] = 'installed'
            
            # Verificar registro se especificado
            if 'registry_keys' in dll_config:
                for reg_key in dll_config['registry_keys']:
                    if self._check_registry_key(reg_key):
                        component_info['registry'] = reg_key
                        component_info['status'] = 'installed'
                        break
            
            return component_info if component_info['status'] == 'installed' else None
            
        except Exception as e:
            self.logger.debug(f"Erro ao detectar componente {component_name}: {e}")
            return None

    def _detect_visual_cpp_redistributables(self) -> List[Dict]:
        """Detecta todas as versões do Visual C++ Redistributable instaladas.
        
        Returns:
            Lista de componentes Visual C++ detectados
        """
        components = []
        detected_versions = set()
        
        try:
            # Chaves de registro para diferentes versões do Visual C++
            vcredist_registry_paths = [
                # Visual C++ 2015-2022 (versões unificadas)
                r'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
                r'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x86',
                r'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
                r'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x86',
                
                # Visual C++ versões anteriores
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
            ]
            
            # Verificar chaves específicas do VC++ Runtime
            for reg_path in vcredist_registry_paths[:4]:  # Primeiras 4 são específicas
                if self._check_registry_key(reg_path):
                    try:
                        version_info = self._get_registry_value(reg_path, 'Version')
                        arch = 'x64' if 'x64' in reg_path else 'x86'
                        
                        if version_info:
                            version_key = f"VC++ 2015-2022 {arch} v{version_info}"
                            if version_key not in detected_versions:
                                detected_versions.add(version_key)
                                components.append({
                                    'name': f'Microsoft Visual C++ 2015-2022 Redistributable ({arch})',
                                    'version': version_info,
                                    'architecture': arch,
                                    'status': 'installed',
                                    'category': 'system_runtime',
                                    'registry_path': reg_path
                                })
                    except Exception as e:
                        self.logger.debug(f"Erro ao ler versão VC++ de {reg_path}: {e}")
            
            # Verificar versões mais antigas através do Uninstall
            for uninstall_path in vcredist_registry_paths[4:]:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_path) as uninstall_key:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(uninstall_key, i)
                                subkey_path = f"{uninstall_path}\\{subkey_name}"
                                
                                display_name = self._get_registry_value(subkey_path, 'DisplayName')
                                if display_name and 'Microsoft Visual C++' in display_name and 'Redistributable' in display_name:
                                    version = self._get_registry_value(subkey_path, 'DisplayVersion') or 'unknown'
                                    
                                    version_key = f"{display_name} v{version}"
                                    if version_key not in detected_versions:
                                        detected_versions.add(version_key)
                                        components.append({
                                            'name': display_name,
                                            'version': version,
                                            'status': 'installed',
                                            'category': 'system_runtime',
                                            'registry_path': subkey_path
                                        })
                                
                                i += 1
                            except OSError:
                                break  # Fim da enumeração
                except Exception as e:
                    self.logger.debug(f"Erro ao enumerar {uninstall_path}: {e}")
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar Visual C++ Redistributables: {e}")
        
        return components

    def _detect_dotnet_framework(self) -> List[Dict]:
        """Detecta versões do .NET Framework e .NET Runtime instaladas.
        
        Returns:
            Lista de componentes .NET detectados
        """
        components = []
        detected_versions = set()
        
        try:
            # Chaves de registro para .NET Framework
            dotnet_registry_paths = [
                r'SOFTWARE\Microsoft\NET Framework Setup\NDP',
                r'SOFTWARE\WOW6432Node\Microsoft\NET Framework Setup\NDP',
                r'SOFTWARE\Microsoft\dotnet\Setup\InstalledVersions',
                r'SOFTWARE\WOW6432Node\Microsoft\dotnet\Setup\InstalledVersions'
            ]
            
            # Detectar .NET Framework tradicional
            for reg_path in dotnet_registry_paths[:2]:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as ndp_key:
                        i = 0
                        while True:
                            try:
                                version_key = winreg.EnumKey(ndp_key, i)
                                if version_key.startswith('v'):
                                    version_path = f"{reg_path}\\{version_key}"
                                    
                                    # Verificar se está instalado
                                    install_value = self._get_registry_value(version_path, 'Install')
                                    if install_value == 1:
                                        version_name = f".NET Framework {version_key}"
                                        if version_name not in detected_versions:
                                            detected_versions.add(version_name)
                                            
                                            # Tentar obter versão específica
                                            specific_version = self._get_registry_value(version_path, 'Version')
                                            
                                            components.append({
                                                'name': f'Microsoft .NET Framework {version_key}',
                                                'version': specific_version or version_key,
                                                'status': 'installed',
                                                'category': 'system_runtime',
                                                'registry_path': version_path
                                            })
                                
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    self.logger.debug(f"Erro ao enumerar .NET Framework em {reg_path}: {e}")
            
            # Detectar .NET Core/.NET 5+ através de arquivos
            dotnet_install_paths = [
                r'C:\Program Files\dotnet',
                r'C:\Program Files (x86)\dotnet'
            ]
            
            for dotnet_path in dotnet_install_paths:
                if PathUtils.exists(dotnet_path):
                    shared_path = os.path.join(dotnet_path, 'shared')
                    if PathUtils.exists(shared_path):
                        try:
                            for runtime_type in os.listdir(shared_path):
                                runtime_path = os.path.join(shared_path, runtime_type)
                                if os.path.isdir(runtime_path):
                                    for version in os.listdir(runtime_path):
                                        version_path = os.path.join(runtime_path, version)
                                        if os.path.isdir(version_path):
                                            runtime_name = f".NET {runtime_type} {version}"
                                            if runtime_name not in detected_versions:
                                                detected_versions.add(runtime_name)
                                                components.append({
                                                    'name': f'Microsoft .NET {runtime_type}',
                                                    'version': version,
                                                    'status': 'installed',
                                                    'category': 'system_runtime',
                                                    'path': version_path
                                                })
                        except Exception as e:
                            self.logger.debug(f"Erro ao enumerar .NET em {dotnet_path}: {e}")
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar .NET Framework: {e}")
        
        return components

    def _detect_directx_runtime(self) -> List[Dict]:
        """Detecta componentes do DirectX Runtime instalados.
        
        Returns:
            Lista de componentes DirectX detectados
        """
        components = []
        
        try:
            # Arquivos principais do DirectX
            directx_files = [
                r'C:\Windows\System32\d3d9.dll',
                r'C:\Windows\System32\d3d11.dll',
                r'C:\Windows\System32\d3d12.dll',
                r'C:\Windows\System32\dxgi.dll',
                r'C:\Windows\System32\xinput1_4.dll',
                r'C:\Windows\System32\xinput1_3.dll',
                r'C:\Windows\System32\d3dcompiler_47.dll'
            ]
            
            detected_files = []
            for file_path in directx_files:
                if PathUtils.exists(file_path):
                    detected_files.append(file_path)
            
            if detected_files:
                components.append({
                    'name': 'Microsoft DirectX Runtime',
                    'files': detected_files,
                    'file_count': len(detected_files),
                    'status': 'installed',
                    'category': 'system_runtime',
                    'path': r'C:\Windows\System32'
                })
            
            # Verificar DirectX End-User Runtime via registro
            directx_registry_paths = [
                r'SOFTWARE\Microsoft\DirectX',
                r'SOFTWARE\WOW6432Node\Microsoft\DirectX'
            ]
            
            for reg_path in directx_registry_paths:
                if self._check_registry_key(reg_path):
                    version = self._get_registry_value(reg_path, 'Version')
                    if version:
                        components.append({
                            'name': 'DirectX End-User Runtime',
                            'version': version,
                            'status': 'installed',
                            'category': 'system_runtime',
                            'registry_path': reg_path
                        })
                        break  # Evitar duplicatas
            
            # Verificar DirectX Redistributable instalado
            uninstall_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_path) as uninstall_key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(uninstall_key, i)
                            subkey_path = f"{uninstall_path}\\{subkey_name}"
                            
                            display_name = self._get_registry_value(subkey_path, 'DisplayName')
                            if display_name and 'DirectX' in display_name and 'Redistributable' in display_name:
                                version = self._get_registry_value(subkey_path, 'DisplayVersion') or 'unknown'
                                
                                components.append({
                                    'name': display_name,
                                    'version': version,
                                    'status': 'installed',
                                    'category': 'system_runtime',
                                    'registry_path': subkey_path
                                })
                                break  # Primeira ocorrência é suficiente
                            
                            i += 1
                        except OSError:
                            break
            except Exception as e:
                self.logger.debug(f"Erro ao verificar DirectX Redistributable: {e}")
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar DirectX Runtime: {e}")
        
        return components

    def _detect_level1_system_runtimes(self) -> Optional[LegacyInstallation]:
        """Detecta runtimes e pré-requisitos do sistema (Nível 1).
        
        Returns:
            Objeto LegacyInstallation com componentes detectados do Nível 1 ou None
        """
        components = []
        
        try:
            self.logger.debug("Detectando runtimes do sistema (Nível 1)...")
            
            # Visual C++ Redistributables - Detecção aprimorada
            vcredist_components = self._detect_visual_cpp_redistributables()
            if vcredist_components:
                components.extend(vcredist_components)
            
            # .NET Framework/Runtime - Detecção aprimorada
            dotnet_components = self._detect_dotnet_framework()
            if dotnet_components:
                components.extend(dotnet_components)
            
            # DirectX Runtime - Detecção aprimorada
            directx_components = self._detect_directx_runtime()
            if directx_components:
                components.extend(directx_components)
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar runtimes do sistema: {e}")
        
        if components:
            return self._create_hierarchical_installation(
                "Nível 1 - Runtimes do Sistema",
                1,
                components
            )
        
        return None

    def _detect_git_for_windows(self) -> List[Dict[str, Any]]:
        """Detecta instalações do Git for Windows de forma robusta.
        
        Returns:
            Lista de componentes Git detectados
        """
        components = []
        
        try:
            # Verificar registro do Windows para Git
            git_registry_keys = [
                r"SOFTWARE\GitForWindows",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Git_is1",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Git_is1"
            ]
            
            git_info = {}
            for reg_key in git_registry_keys:
                if self._check_registry_key(reg_key):
                    git_info['registry'] = reg_key
                    # Tentar obter versão do registro
                    version = self._get_registry_value(reg_key, "DisplayVersion")
                    if version:
                        git_info['version'] = version
                    break
            
            # Procurar executável do Git no PATH
            git_path = self._find_executable_in_path('git.exe')
            
            # Procurar em caminhos comuns
            common_git_paths = [
                r"C:\Program Files\Git\bin\git.exe",
                r"C:\Program Files (x86)\Git\bin\git.exe",
                r"C:\Git\bin\git.exe",
                r"C:\tools\git\bin\git.exe"
            ]
            
            if not git_path:
                for path in common_git_paths:
                    if PathUtils.exists(path):
                        git_path = path
                        break
            
            # Verificar Git Bash
            git_bash_paths = [
                r"C:\Program Files\Git\git-bash.exe",
                r"C:\Program Files (x86)\Git\git-bash.exe"
            ]
            
            git_bash_path = None
            for path in git_bash_paths:
                if PathUtils.exists(path):
                    git_bash_path = path
                    break
            
            if git_info or git_path or git_bash_path:
                components.append({
                    'name': 'Git for Windows',
                    'path': git_path or git_bash_path or 'Registry detected',
                    'registry': git_info.get('registry'),
                    'version': git_info.get('version', 'unknown'),
                    'status': 'installed',
                    'category': 'emudeck_tool',
                    'details': {
                        'git_executable': git_path,
                        'git_bash': git_bash_path,
                        'registry_key': git_info.get('registry')
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Git for Windows: {e}")
        
        return components

    def _detect_7zip(self) -> List[Dict[str, Any]]:
        """Detecta instalações do 7-Zip de forma robusta.
        
        Returns:
            Lista de componentes 7-Zip detectados
        """
        components = []
        
        try:
            # Verificar registro do Windows para 7-Zip
            zip_registry_keys = [
                r"SOFTWARE\7-Zip",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\7-Zip",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\7-Zip"
            ]
            
            zip_info = {}
            for reg_key in zip_registry_keys:
                if self._check_registry_key(reg_key):
                    zip_info['registry'] = reg_key
                    # Tentar obter versão e caminho do registro
                    version = self._get_registry_value(reg_key, "DisplayVersion")
                    install_path = self._get_registry_value(reg_key, "InstallLocation")
                    if version:
                        zip_info['version'] = version
                    if install_path:
                        zip_info['install_path'] = install_path
                    break
            
            # Procurar executável do 7-Zip
            zip_paths = [
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
                r"C:\7-Zip\7z.exe"
            ]
            
            if zip_info.get('install_path'):
                zip_paths.insert(0, os.path.join(zip_info['install_path'], '7z.exe'))
            
            zip_path = None
            for path in zip_paths:
                if PathUtils.exists(path):
                    zip_path = path
                    break
            
            # Verificar 7-Zip GUI
            gui_paths = [
                r"C:\Program Files\7-Zip\7zFM.exe",
                r"C:\Program Files (x86)\7-Zip\7zFM.exe"
            ]
            
            gui_path = None
            for path in gui_paths:
                if PathUtils.exists(path):
                    gui_path = path
                    break
            
            if zip_info or zip_path or gui_path:
                components.append({
                    'name': '7-Zip',
                    'path': zip_path or gui_path or zip_info.get('install_path', 'Registry detected'),
                    'registry': zip_info.get('registry'),
                    'version': zip_info.get('version', 'unknown'),
                    'status': 'installed',
                    'category': 'emudeck_tool',
                    'details': {
                        'console_executable': zip_path,
                        'gui_executable': gui_path,
                        'install_location': zip_info.get('install_path'),
                        'registry_key': zip_info.get('registry')
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar 7-Zip: {e}")
        
        return components

    def _detect_powershell_core(self) -> List[Dict[str, Any]]:
        """Detecta instalações do PowerShell Core de forma robusta.
        
        Returns:
            Lista de componentes PowerShell Core detectados
        """
        components = []
        
        try:
            # Procurar PowerShell Core no PATH
            pwsh_path = self._find_executable_in_path('pwsh.exe')
            
            # Procurar em caminhos comuns
            common_pwsh_paths = [
                r"C:\Program Files\PowerShell\7\pwsh.exe",
                r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
                r"C:\Users\{}\AppData\Local\Microsoft\powershell\pwsh.exe".format(os.environ.get('USERNAME', '')),
                r"C:\tools\powershell\pwsh.exe"
            ]
            
            if not pwsh_path:
                for path in common_pwsh_paths:
                    if PathUtils.exists(path):
                        pwsh_path = path
                        break
            
            # Verificar registro para PowerShell Core
            pwsh_registry_keys = [
                r"SOFTWARE\Microsoft\PowerShellCore",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{1D00D1DC-9C3B-4B76-8F3A-1D18F5B98C2D}",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{1D00D1DC-9C3B-4B76-8F3A-1D18F5B98C2D}"
            ]
            
            pwsh_info = {}
            for reg_key in pwsh_registry_keys:
                if self._check_registry_key(reg_key):
                    pwsh_info['registry'] = reg_key
                    version = self._get_registry_value(reg_key, "DisplayVersion")
                    if version:
                        pwsh_info['version'] = version
                    break
            
            # Tentar obter versão executando o comando
            version_info = None
            if pwsh_path:
                try:
                    result = subprocess.run([pwsh_path, '-Command', '$PSVersionTable.PSVersion.ToString()'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version_info = result.stdout.strip()
                except Exception:
                    pass
            
            if pwsh_path or pwsh_info:
                components.append({
                    'name': 'PowerShell Core',
                    'path': pwsh_path or 'Registry detected',
                    'registry': pwsh_info.get('registry'),
                    'version': version_info or pwsh_info.get('version', 'unknown'),
                    'status': 'installed',
                    'category': 'emudeck_tool',
                    'details': {
                        'executable': pwsh_path,
                        'detected_version': version_info,
                        'registry_version': pwsh_info.get('version'),
                        'registry_key': pwsh_info.get('registry')
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar PowerShell Core: {e}")
        
        return components

    def _detect_level2_emudeck_dependencies(self) -> Optional[LegacyInstallation]:
        """Detecta dependências da ferramenta EmuDeck (Nível 2).
        
        Returns:
            Objeto LegacyInstallation com componentes detectados do Nível 2 ou None
        """
        components = []
        
        try:
            self.logger.debug("Detectando dependências EmuDeck (Nível 2)...")
            
            # Git for Windows - Detecção aprimorada
            git_components = self._detect_git_for_windows()
            if git_components:
                components.extend(git_components)
            
            # 7-Zip - Detecção aprimorada
            zip_components = self._detect_7zip()
            if zip_components:
                components.extend(zip_components)
            
            # PowerShell Core - Detecção aprimorada
            pwsh_components = self._detect_powershell_core()
            if pwsh_components:
                components.extend(pwsh_components)
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar dependências EmuDeck: {e}")
        
        if components:
            return self._create_hierarchical_installation(
                "Nível 2 - Dependências EmuDeck",
                2,
                components
            )
        
        return components

    def _detect_steam(self) -> List[Dict[str, Any]]:
        """Detecta instalações do Steam de forma robusta.
        
        Returns:
            Lista de componentes Steam detectados
        """
        components = []
        
        try:
            # Verificar registro do Windows para Steam
            steam_registry_keys = [
                r"SOFTWARE\Valve\Steam",
                r"SOFTWARE\WOW6432Node\Valve\Steam"
            ]
            
            steam_info = {}
            for reg_key in steam_registry_keys:
                if self._check_registry_key(reg_key):
                    steam_info['registry'] = reg_key
                    install_path = self._get_registry_value(reg_key, "InstallPath")
                    if install_path:
                        steam_info['install_path'] = install_path
                    break
            
            # Procurar executável do Steam
            steam_paths = [
                r"C:\Program Files (x86)\Steam\steam.exe",
                r"C:\Program Files\Steam\steam.exe",
                r"C:\Steam\steam.exe"
            ]
            
            if steam_info.get('install_path'):
                steam_paths.insert(0, os.path.join(steam_info['install_path'], 'steam.exe'))
            
            steam_path = None
            for path in steam_paths:
                if PathUtils.exists(path):
                    steam_path = path
                    break
            
            if steam_info or steam_path:
                components.append({
                    'name': 'Steam',
                    'path': steam_path or steam_info.get('install_path', 'Registry detected'),
                    'registry': steam_info.get('registry'),
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'critical': True,  # Steam é obrigatório
                    'details': {
                        'executable': steam_path,
                        'install_path': steam_info.get('install_path'),
                        'registry_key': steam_info.get('registry')
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Steam: {e}")
        
        return components

    def _detect_steam_input(self) -> List[Dict[str, Any]]:
        """Detecta Steam Input Layer de forma robusta.
        
        Returns:
            Lista de componentes Steam Input detectados
        """
        components = []
        
        try:
            # Primeiro detectar Steam
            steam_components = self._detect_steam()
            if not steam_components:
                return components
            
            steam_install_path = steam_components[0]['details'].get('install_path')
            if not steam_install_path:
                return components
            
            # Verificar componentes do Steam Input
            steam_input_paths = [
                os.path.join(steam_install_path, 'controller_config'),
                os.path.join(steam_install_path, 'config', 'controller_config'),
                os.path.join(steam_install_path, 'steamapps', 'common', 'SteamController')
            ]
            
            found_paths = []
            for path in steam_input_paths:
                if PathUtils.exists(path):
                    found_paths.append(path)
            
            if found_paths:
                components.append({
                    'name': 'Steam Input Layer',
                    'path': found_paths[0],
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'critical': True,  # Steam Input é crítico para controles
                    'details': {
                        'controller_config_paths': found_paths,
                        'steam_install_path': steam_install_path
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Steam Input: {e}")
        
        return components

    def _detect_sdl2(self) -> List[Dict[str, Any]]:
        """Detecta SDL2 de forma robusta.
        
        Returns:
            Lista de componentes SDL2 detectados
        """
        components = []
        
        try:
            # Procurar DLLs do SDL2
            sdl2_dlls = [
                'SDL2.dll',
                'SDL2_image.dll',
                'SDL2_mixer.dll',
                'SDL2_ttf.dll',
                'SDL2_net.dll'
            ]
            
            found_files = []
            for dll_name in sdl2_dlls:
                dll_files = self._find_dll_in_system(dll_name)
                found_files.extend(dll_files)
            
            if found_files:
                components.append({
                    'name': 'SDL2 (Simple DirectMedia Layer)',
                    'path': found_files[0],
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'details': {
                        'dll_files': found_files,
                        'core_dlls': [f for f in found_files if 'SDL2.dll' in f],
                        'extension_dlls': [f for f in found_files if 'SDL2_' in f]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar SDL2: {e}")
        
        return components

    def _detect_boost_cpp(self) -> List[Dict[str, Any]]:
        """Detecta Boost C++ Libraries de forma robusta.
        
        Returns:
            Lista de componentes Boost detectados
        """
        components = []
        
        try:
            import glob
            
            # Procurar DLLs do Boost
            boost_patterns = [
                'boost_filesystem*.dll',
                'boost_locale*.dll', 
                'boost_system*.dll',
                'libboost_*.dll'
            ]
            
            search_paths = [
                'C:\\Windows\\System32',
                'C:\\Windows\\SysWOW64',
                'C:\\Program Files\\boost*',
                'C:\\Program Files (x86)\\boost*',
                'C:\\vcpkg\\installed\\*\\bin'
            ]
            
            found_files = []
            for pattern in boost_patterns:
                for search_path in search_paths:
                    if '*' in search_path:
                        base_paths = glob.glob(search_path)
                        for base_path in base_paths:
                            if os.path.isdir(base_path):
                                matches = glob.glob(os.path.join(base_path, pattern))
                                found_files.extend(matches)
                                # Busca recursiva em subdiretórios
                                matches = glob.glob(os.path.join(base_path, '**', pattern), recursive=True)
                                found_files.extend(matches)
                    else:
                        matches = glob.glob(os.path.join(search_path, pattern))
                        found_files.extend(matches)
            
            # Remover duplicatas
            found_files = list(set(found_files))
            
            if found_files:
                components.append({
                    'name': 'Boost C++ Libraries',
                    'path': found_files[0],
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'details': {
                        'dll_files': found_files[:20],  # Limitar para não sobrecarregar
                        'filesystem_dlls': [f for f in found_files if 'filesystem' in f],
                        'locale_dlls': [f for f in found_files if 'locale' in f],
                        'system_dlls': [f for f in found_files if 'system' in f]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Boost C++: {e}")
        
        return components

    def _detect_curl(self) -> List[Dict[str, Any]]:
        """Detecta cURL de forma robusta.
        
        Returns:
            Lista de componentes cURL detectados
        """
        components = []
        
        try:
            # Procurar DLLs do cURL
            curl_dlls = ['libcurl.dll', 'curl.dll', 'libcurl-4.dll']
            
            found_files = []
            for dll_name in curl_dlls:
                dll_files = self._find_dll_in_system(dll_name)
                found_files.extend(dll_files)
            
            # Procurar executável curl
            curl_exe = self._find_executable_in_path('curl.exe')
            
            if found_files or curl_exe:
                components.append({
                    'name': 'cURL Library',
                    'path': found_files[0] if found_files else curl_exe,
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'details': {
                        'dll_files': found_files,
                        'executable': curl_exe,
                        'library_dlls': [f for f in found_files if 'libcurl' in f],
                        'curl_dlls': [f for f in found_files if 'curl.dll' in f]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar cURL: {e}")
        
        return components

    def _detect_freeimage(self) -> List[Dict[str, Any]]:
        """Detecta FreeImage de forma robusta.
        
        Returns:
            Lista de componentes FreeImage detectados
        """
        components = []
        
        try:
            # Procurar DLLs do FreeImage
            freeimage_dlls = ['FreeImage.dll', 'libfreeimage.dll', 'FreeImagePlus.dll']
            
            found_files = []
            for dll_name in freeimage_dlls:
                dll_files = self._find_dll_in_system(dll_name)
                found_files.extend(dll_files)
            
            if found_files:
                components.append({
                    'name': 'FreeImage Library',
                    'path': found_files[0],
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'details': {
                        'dll_files': found_files,
                        'core_dlls': [f for f in found_files if 'FreeImage.dll' in f],
                        'plus_dlls': [f for f in found_files if 'FreeImagePlus' in f]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar FreeImage: {e}")
        
        return components

    def _detect_freetype(self) -> List[Dict[str, Any]]:
        """Detecta FreeType de forma robusta.
        
        Returns:
            Lista de componentes FreeType detectados
        """
        components = []
        
        try:
            # Procurar DLLs do FreeType
            freetype_dlls = ['freetype.dll', 'libfreetype.dll', 'freetype6.dll']
            
            found_files = []
            for dll_name in freetype_dlls:
                dll_files = self._find_dll_in_system(dll_name)
                found_files.extend(dll_files)
            
            if found_files:
                components.append({
                    'name': 'FreeType Library',
                    'path': found_files[0],
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'details': {
                        'dll_files': found_files,
                        'freetype_dlls': [f for f in found_files if 'freetype' in f.lower()]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar FreeType: {e}")
        
        return components

    def _detect_eigen(self) -> List[Dict[str, Any]]:
        """Detecta Eigen Math Library de forma robusta.
        
        Returns:
            Lista de componentes Eigen detectados
        """
        components = []
        
        try:
            # Procurar headers do Eigen em locais comuns
            common_include_paths = [
                'C:\\Program Files\\Eigen3\\include',
                'C:\\Program Files (x86)\\Eigen3\\include',
                'C:\\vcpkg\\installed\\x64-windows\\include',
                'C:\\vcpkg\\installed\\x86-windows\\include',
                'C:\\msys64\\mingw64\\include',
                'C:\\msys64\\mingw32\\include',
                'C:\\MinGW\\include',
                'C:\\tools\\eigen\\include'
            ]
            
            eigen_paths = []
            for include_path in common_include_paths:
                eigen_header_path = os.path.join(include_path, 'Eigen', 'Dense')
                eigen_core_path = os.path.join(include_path, 'Eigen', 'Core')
                
                if PathUtils.exists(eigen_header_path) or PathUtils.exists(eigen_core_path):
                    eigen_paths.append(include_path)
            
            if eigen_paths:
                components.append({
                    'name': 'Eigen Math Library',
                    'path': eigen_paths[0],
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'type': 'header_library',
                    'details': {
                        'include_paths': eigen_paths,
                        'header_type': 'C++ Template Library',
                        'primary_path': eigen_paths[0]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Eigen: {e}")
        
        return components

    def _detect_vlc(self) -> List[Dict[str, Any]]:
        """Detecta VLC Media Player de forma robusta.
        
        Returns:
            Lista de componentes VLC detectados
        """
        components = []
        
        try:
            # Verificar registro do Windows para VLC
            vlc_registry_keys = [
                r"SOFTWARE\VideoLAN\VLC",
                r"SOFTWARE\WOW6432Node\VideoLAN\VLC",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player"
            ]
            
            vlc_info = {}
            for reg_key in vlc_registry_keys:
                if self._check_registry_key(reg_key):
                    vlc_info['registry'] = reg_key
                    install_path = self._get_registry_value(reg_key, "InstallDir")
                    if install_path:
                        vlc_info['install_path'] = install_path
                    break
            
            # Procurar executável do VLC
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
                r"C:\VLC\vlc.exe"
            ]
            
            if vlc_info.get('install_path'):
                vlc_paths.insert(0, os.path.join(vlc_info['install_path'], 'vlc.exe'))
            
            vlc_path = None
            for path in vlc_paths:
                if PathUtils.exists(path):
                    vlc_path = path
                    break
            
            # Procurar DLLs do VLC
            vlc_dlls = ['libvlc.dll', 'libvlccore.dll']
            found_dlls = []
            for dll_name in vlc_dlls:
                dll_files = self._find_dll_in_system(dll_name)
                found_dlls.extend(dll_files)
            
            if vlc_info or vlc_path or found_dlls:
                components.append({
                    'name': 'VLC Media Player',
                    'path': vlc_path or vlc_info.get('install_path', found_dlls[0] if found_dlls else 'Registry detected'),
                    'registry': vlc_info.get('registry'),
                    'status': 'installed',
                    'category': 'frontend_backend',
                    'details': {
                        'executable': vlc_path,
                        'install_path': vlc_info.get('install_path'),
                        'dll_files': found_dlls,
                        'registry_key': vlc_info.get('registry')
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar VLC: {e}")
        
        return components

    def _detect_level3_frontend_backend(self) -> Optional[LegacyInstallation]:
        """Detecta dependências de frontend/backend (Nível 3).
        
        Returns:
            Objeto LegacyInstallation com componentes detectados do Nível 3 ou None
        """
        components = []
        
        try:
            self.logger.debug("Detectando dependências frontend/backend (Nível 3)...")
            
            # Steam (obrigatório) - Detecção aprimorada
            steam_components = self._detect_steam()
            if steam_components:
                components.extend(steam_components)
            
            # Steam Input - Detecção específica
            steam_input_components = self._detect_steam_input()
            if steam_input_components:
                components.extend(steam_input_components)
            
            # SDL2 - Detecção aprimorada
            sdl2_components = self._detect_sdl2()
            if sdl2_components:
                components.extend(sdl2_components)
            
            # Boost C++ Libraries - Detecção aprimorada
            boost_components = self._detect_boost_cpp()
            if boost_components:
                components.extend(boost_components)
            
            # cURL - Detecção aprimorada
            curl_components = self._detect_curl()
            if curl_components:
                components.extend(curl_components)
            
            # FreeImage - Detecção aprimorada
            freeimage_components = self._detect_freeimage()
            if freeimage_components:
                components.extend(freeimage_components)
            
            # FreeType - Detecção aprimorada
            freetype_components = self._detect_freetype()
            if freetype_components:
                components.extend(freetype_components)
            
            # Eigen - Detecção aprimorada
            eigen_components = self._detect_eigen()
            if eigen_components:
                components.extend(eigen_components)
            
            # VLC - Detecção aprimorada
            vlc_components = self._detect_vlc()
            if vlc_components:
                components.extend(vlc_components)
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar dependências frontend/backend: {e}")
        
        if components:
            return self._create_hierarchical_installation(
                "Nível 3 - Frontend/Backend",
                3,
                components
            )
        
        return components

    def _detect_retroarch(self) -> List[Dict[str, Any]]:
        """Detecta RetroArch de forma robusta.
        
        Returns:
            Lista de componentes RetroArch detectados
        """
        components = []
        
        try:
            # Verificar registro do Windows para RetroArch
            retroarch_registry_keys = [
                r"SOFTWARE\RetroArch",
                r"SOFTWARE\WOW6432Node\RetroArch",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\RetroArch",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\RetroArch"
            ]
            
            retroarch_info = {}
            for reg_key in retroarch_registry_keys:
                if self._check_registry_key(reg_key):
                    retroarch_info['registry'] = reg_key
                    install_path = self._get_registry_value(reg_key, "InstallLocation")
                    if install_path:
                        retroarch_info['install_path'] = install_path
                    break
            
            # Procurar executável do RetroArch
            retroarch_paths = [
                r"C:\RetroArch\retroarch.exe",
                r"C:\Program Files\RetroArch\retroarch.exe",
                r"C:\Program Files (x86)\RetroArch\retroarch.exe"
            ]
            
            if retroarch_info.get('install_path'):
                retroarch_paths.insert(0, os.path.join(retroarch_info['install_path'], 'retroarch.exe'))
            
            retroarch_path = None
            for path in retroarch_paths:
                if PathUtils.exists(path):
                    retroarch_path = path
                    break
            
            # Procurar arquivo de configuração
            config_paths = []
            if retroarch_path:
                config_dir = os.path.dirname(retroarch_path)
                config_file = os.path.join(config_dir, 'retroarch.cfg')
                if PathUtils.exists(config_file):
                    config_paths.append(config_file)
            
            if retroarch_info or retroarch_path:
                components.append({
                    'name': 'RetroArch',
                    'path': retroarch_path or retroarch_info.get('install_path', 'Registry detected'),
                    'registry': retroarch_info.get('registry'),
                    'status': 'installed',
                    'category': 'emulator',
                    'critical': True,  # RetroArch é um emulador central
                    'details': {
                        'executable': retroarch_path,
                        'install_path': retroarch_info.get('install_path'),
                        'config_files': config_paths,
                        'registry_key': retroarch_info.get('registry')
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar RetroArch: {e}")
        
        return components

    def _detect_pcsx2(self) -> List[Dict[str, Any]]:
        """Detecta PCSX2 de forma robusta.
        
        Returns:
            Lista de componentes PCSX2 detectados
        """
        components = []
        
        try:
            # Procurar executável do PCSX2
            pcsx2_paths = [
                r"C:\Program Files\PCSX2\pcsx2.exe",
                r"C:\Program Files (x86)\PCSX2\pcsx2.exe",
                r"C:\PCSX2\pcsx2.exe",
                r"C:\Program Files\PCSX2\PCSX2.exe",
                r"C:\Program Files (x86)\PCSX2\PCSX2.exe"
            ]
            
            pcsx2_path = None
            for path in pcsx2_paths:
                if PathUtils.exists(path):
                    pcsx2_path = path
                    break
            
            # Procurar via PATH
            if not pcsx2_path:
                pcsx2_path = self._find_executable_in_path('pcsx2.exe')
                if not pcsx2_path:
                    pcsx2_path = self._find_executable_in_path('PCSX2.exe')
            
            if pcsx2_path:
                components.append({
                    'name': 'PCSX2 (PlayStation 2 Emulator)',
                    'path': pcsx2_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': pcsx2_path,
                        'platform': 'PlayStation 2',
                        'install_dir': os.path.dirname(pcsx2_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar PCSX2: {e}")
        
        return components

    def _detect_dolphin(self) -> List[Dict[str, Any]]:
        """Detecta Dolphin de forma robusta.
        
        Returns:
            Lista de componentes Dolphin detectados
        """
        components = []
        
        try:
            # Procurar executável do Dolphin
            dolphin_paths = [
                r"C:\Program Files\Dolphin-x64\Dolphin.exe",
                r"C:\Program Files (x86)\Dolphin-x64\Dolphin.exe",
                r"C:\Dolphin\Dolphin.exe",
                r"C:\Program Files\Dolphin\Dolphin.exe",
                r"C:\Program Files (x86)\Dolphin\Dolphin.exe"
            ]
            
            dolphin_path = None
            for path in dolphin_paths:
                if PathUtils.exists(path):
                    dolphin_path = path
                    break
            
            # Procurar via PATH
            if not dolphin_path:
                dolphin_path = self._find_executable_in_path('Dolphin.exe')
            
            if dolphin_path:
                components.append({
                    'name': 'Dolphin (GameCube/Wii Emulator)',
                    'path': dolphin_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': dolphin_path,
                        'platform': 'GameCube/Wii',
                        'install_dir': os.path.dirname(dolphin_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Dolphin: {e}")
        
        return components

    def _detect_rpcs3(self) -> List[Dict[str, Any]]:
        """Detecta RPCS3 de forma robusta.
        
        Returns:
            Lista de componentes RPCS3 detectados
        """
        components = []
        
        try:
            # Procurar executável do RPCS3
            rpcs3_paths = [
                r"C:\Program Files\RPCS3\rpcs3.exe",
                r"C:\Program Files (x86)\RPCS3\rpcs3.exe",
                r"C:\RPCS3\rpcs3.exe"
            ]
            
            rpcs3_path = None
            for path in rpcs3_paths:
                if PathUtils.exists(path):
                    rpcs3_path = path
                    break
            
            # Procurar via PATH
            if not rpcs3_path:
                rpcs3_path = self._find_executable_in_path('rpcs3.exe')
            
            if rpcs3_path:
                components.append({
                    'name': 'RPCS3 (PlayStation 3 Emulator)',
                    'path': rpcs3_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': rpcs3_path,
                        'platform': 'PlayStation 3',
                        'install_dir': os.path.dirname(rpcs3_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar RPCS3: {e}")
        
        return components

    def _detect_cemu(self) -> List[Dict[str, Any]]:
        """Detecta Cemu de forma robusta.
        
        Returns:
            Lista de componentes Cemu detectados
        """
        components = []
        
        try:
            # Procurar executável do Cemu
            cemu_paths = [
                r"C:\Program Files\Cemu\Cemu.exe",
                r"C:\Program Files (x86)\Cemu\Cemu.exe",
                r"C:\Cemu\Cemu.exe"
            ]
            
            cemu_path = None
            for path in cemu_paths:
                if PathUtils.exists(path):
                    cemu_path = path
                    break
            
            # Procurar via PATH
            if not cemu_path:
                cemu_path = self._find_executable_in_path('Cemu.exe')
            
            if cemu_path:
                components.append({
                    'name': 'Cemu (Wii U Emulator)',
                    'path': cemu_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': cemu_path,
                        'platform': 'Wii U',
                        'install_dir': os.path.dirname(cemu_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Cemu: {e}")
        
        return components

    def _detect_yuzu(self) -> List[Dict[str, Any]]:
        """Detecta Yuzu de forma robusta.
        
        Returns:
            Lista de componentes Yuzu detectados
        """
        components = []
        
        try:
            # Procurar executável do Yuzu
            yuzu_paths = [
                r"C:\Program Files\yuzu\yuzu.exe",
                r"C:\Program Files (x86)\yuzu\yuzu.exe",
                r"C:\yuzu\yuzu.exe"
            ]
            
            yuzu_path = None
            for path in yuzu_paths:
                if PathUtils.exists(path):
                    yuzu_path = path
                    break
            
            # Procurar via PATH
            if not yuzu_path:
                yuzu_path = self._find_executable_in_path('yuzu.exe')
            
            if yuzu_path:
                components.append({
                    'name': 'Yuzu (Nintendo Switch Emulator)',
                    'path': yuzu_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': yuzu_path,
                        'platform': 'Nintendo Switch',
                        'install_dir': os.path.dirname(yuzu_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Yuzu: {e}")
        
        return components

    def _detect_ryujinx(self) -> List[Dict[str, Any]]:
        """Detecta Ryujinx de forma robusta.
        
        Returns:
            Lista de componentes Ryujinx detectados
        """
        components = []
        
        try:
            # Procurar executável do Ryujinx
            ryujinx_paths = [
                r"C:\Program Files\Ryujinx\Ryujinx.exe",
                r"C:\Program Files (x86)\Ryujinx\Ryujinx.exe",
                r"C:\Ryujinx\Ryujinx.exe"
            ]
            
            ryujinx_path = None
            for path in ryujinx_paths:
                if PathUtils.exists(path):
                    ryujinx_path = path
                    break
            
            # Procurar via PATH
            if not ryujinx_path:
                ryujinx_path = self._find_executable_in_path('Ryujinx.exe')
            
            if ryujinx_path:
                components.append({
                    'name': 'Ryujinx (Nintendo Switch Emulator)',
                    'path': ryujinx_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': ryujinx_path,
                        'platform': 'Nintendo Switch',
                        'install_dir': os.path.dirname(ryujinx_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar Ryujinx: {e}")
        
        return components

    def _detect_mame(self) -> List[Dict[str, Any]]:
        """Detecta MAME de forma robusta.
        
        Returns:
            Lista de componentes MAME detectados
        """
        components = []
        
        try:
            # Procurar executável do MAME
            mame_paths = [
                r"C:\Program Files\MAME\mame.exe",
                r"C:\Program Files (x86)\MAME\mame.exe",
                r"C:\MAME\mame.exe",
                r"C:\Program Files\MAME\mame64.exe",
                r"C:\Program Files (x86)\MAME\mame64.exe",
                r"C:\MAME\mame64.exe"
            ]
            
            mame_path = None
            for path in mame_paths:
                if PathUtils.exists(path):
                    mame_path = path
                    break
            
            # Procurar via PATH
            if not mame_path:
                mame_path = self._find_executable_in_path('mame.exe')
                if not mame_path:
                    mame_path = self._find_executable_in_path('mame64.exe')
            
            if mame_path:
                components.append({
                    'name': 'MAME (Multiple Arcade Machine Emulator)',
                    'path': mame_path,
                    'status': 'installed',
                    'category': 'emulator',
                    'details': {
                        'executable': mame_path,
                        'platform': 'Arcade',
                        'install_dir': os.path.dirname(mame_path)
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Erro ao detectar MAME: {e}")
        
        return components

    def _detect_level4_emulator_dependencies(self) -> Optional[LegacyInstallation]:
        """Detecta dependências específicas de emuladores (Nível 4).
        
        Returns:
            Objeto LegacyInstallation com componentes detectados do Nível 4 ou None
        """
        components = []
        
        try:
            self.logger.debug("Detectando emuladores (Nível 4)...")
            
            # RetroArch - Detecção aprimorada
            retroarch_components = self._detect_retroarch()
            if retroarch_components:
                components.extend(retroarch_components)
            
            # PCSX2 - Detecção aprimorada
            pcsx2_components = self._detect_pcsx2()
            if pcsx2_components:
                components.extend(pcsx2_components)
            
            # Dolphin - Detecção aprimorada
            dolphin_components = self._detect_dolphin()
            if dolphin_components:
                components.extend(dolphin_components)
            
            # RPCS3 - Detecção aprimorada
            rpcs3_components = self._detect_rpcs3()
            if rpcs3_components:
                components.extend(rpcs3_components)
            
            # Cemu - Detecção aprimorada
            cemu_components = self._detect_cemu()
            if cemu_components:
                components.extend(cemu_components)
            
            # Yuzu - Detecção aprimorada
            yuzu_components = self._detect_yuzu()
            if yuzu_components:
                components.extend(yuzu_components)
            
            # Ryujinx - Detecção aprimorada
            ryujinx_components = self._detect_ryujinx()
            if ryujinx_components:
                components.extend(ryujinx_components)
            
            # MAME - Detecção aprimorada
            mame_components = self._detect_mame()
            if mame_components:
                components.extend(mame_components)
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar emuladores: {e}")
        
        if components:
            return self._create_hierarchical_installation(
                "Nível 4 - Emuladores",
                4,
                components
            )
        
        return None

    def _detect_es_de_installation(self) -> Optional[LegacyInstallation]:
        """Detecta instalação do EmulationStation-DE."""
        try:
            self.logger.debug("Procurando instalação do EmulationStation-DE...")
            
            # Expandir padrões de caminho
            installation_paths = self._expand_path_patterns(self.es_de_patterns['installation_paths'])
            
            # Procurar por diretórios de instalação
            for install_path in installation_paths:
                if not PathUtils.exists(install_path):
                    continue
                
                self.logger.debug(f"Encontrado diretório ES-DE: {install_path}")
                
                # Criar objeto de instalação
                installation = LegacyInstallation(
                    name="EmulationStation-DE",
                    path=install_path,
                    installation_type="es-de"
                )
                
                # Detectar versão
                version = self._detect_es_de_version(install_path)
                installation.version = version
                
                # Procurar componentes
                self._scan_es_de_components(installation, install_path)
                
                # Calcular tamanho total
                installation.calculate_total_size()
                
                self.logger.info(f"EmulationStation-DE detectado em: {install_path} (versão: {version})")
                return installation
            
            self.logger.debug("Nenhuma instalação do EmulationStation-DE encontrada")
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar EmulationStation-DE: {e}")
            return None
    
    def _detect_es_de_version(self, install_path: str) -> str:
        """Detecta a versão do EmulationStation-DE instalado."""
        try:
            # Procurar por arquivos de configuração com informações de versão
            version_files = ['version.txt', 'VERSION', 'es_settings.xml']
            
            for version_file in version_files:
                version_path = os.path.join(install_path, version_file)
                if not PathUtils.exists(version_path):
                    continue
                
                try:
                    content = FileUtils.read_file(version_path)
                    
                    if version_file.endswith('.xml'):
                        # Procurar por tag de versão no XML
                        import re
                        version_match = re.search(r'<string name="ApplicationVersion" value="([^"]+)"', content)
                        if version_match:
                            return version_match.group(1)
                    else:
                        # Arquivo de texto simples
                        lines = content.strip().split('\n')
                        if lines:
                            return lines[0].strip()
                            
                except Exception:
                    continue
            
            # Fallback: tentar detectar pela presença de executáveis
            for executable in self.es_de_patterns['executables']:
                exe_path = os.path.join(install_path, executable)
                if PathUtils.exists(exe_path):
                    return "detected"
            
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Erro ao detectar versão do ES-DE: {e}")
            return "unknown"
    
    def _scan_es_de_components(self, installation: LegacyInstallation, install_path: str) -> None:
        """Escaneia componentes da instalação do EmulationStation-DE."""
        try:
            # Procurar executáveis
            for executable in self.es_de_patterns['executables']:
                exe_path = os.path.join(install_path, executable)
                if PathUtils.exists(exe_path):
                    installation.add_component(
                        exe_path, 'executable',
                        f'Executável principal do ES-DE: {executable}'
                    )
            
            # Procurar arquivos de configuração
            for config_file in self.es_de_patterns['config_files']:
                config_path = os.path.join(install_path, config_file)
                if PathUtils.exists(config_path):
                    installation.add_component(
                        config_path, 'config',
                        f'Arquivo de configuração: {config_file}'
                    )
            
            # Procurar diretórios de dados
            for data_dir in self.es_de_patterns['data_directories']:
                data_path = os.path.join(install_path, data_dir)
                if PathUtils.exists(data_path):
                    installation.add_component(
                        data_path, 'data',
                        f'Diretório de dados: {data_dir}'
                    )
            
            # Escanear subdiretórios para componentes adicionais
            try:
                for item in os.listdir(install_path):
                    item_path = os.path.join(install_path, item)
                    
                    if os.path.isdir(item_path):
                        # Verificar se é um diretório importante
                        if item.lower() in ['themes', 'systems', 'media']:
                            installation.add_component(
                                item_path, 'data',
                                f'Diretório do sistema: {item}'
                            )
                    elif os.path.isfile(item_path):
                        # Verificar se é um arquivo importante
                        if item.lower().endswith(('.xml', '.cfg', '.json')):
                            installation.add_component(
                                item_path, 'config',
                                f'Arquivo de configuração: {item}'
                            )
                            
            except Exception as e:
                self.logger.warning(f"Erro ao escanear subdiretórios do ES-DE: {e}")
                
        except Exception as e:
            self.logger.error(f"Erro ao escanear componentes do ES-DE: {e}")
    
    def scan_for_legacy_installations(self, force_rescan: bool = False) -> Dict[str, LegacyInstallation]:
        """Executa scan completo para detectar instalações legadas.
        
        Args:
            force_rescan: Força novo scan mesmo se já foi executado recentemente
            
        Returns:
            Dicionário com instalações detectadas
        """
        try:
            # Verificar se scan já está em progresso
            if self._scan_in_progress:
                self.logger.warning("Scan já está em progresso")
                return self._detected_installations.copy()
            
            # Verificar se precisa fazer novo scan
            if not force_rescan and self._last_scan_time:
                elapsed = (datetime.now() - self._last_scan_time).total_seconds()
                if elapsed < 300:  # Não fazer scan se foi executado há menos de 5 minutos
                    self.logger.debug("Usando resultados do scan anterior")
                    return self._detected_installations.copy()
            
            self._scan_in_progress = True
            self.logger.info("Iniciando scan para instalações legadas...")
            
            # Limpar detecções anteriores
            self._detected_installations.clear()
            
            # Verificar se há drives disponíveis
            if not self._verify_available_drives():
                self.logger.error("Nenhum drive disponível para scan")
                return {}
            
            # Detectar EmuDeck
            emudeck_installation = self._detect_emudeck_installation()
            if emudeck_installation:
                self._detected_installations['emudeck'] = emudeck_installation
            
            # Detectar EmulationStation-DE
            es_de_installation = self._detect_es_de_installation()
            if es_de_installation:
                self._detected_installations['es-de'] = es_de_installation
            
            # Detectar componentes do ecossistema EmuDeck por nível hierárquico
            self.logger.info("Detectando componentes do ecossistema EmuDeck...")
            
            # Nível 1: Runtimes do Sistema
            level1_components = self._detect_level1_system_runtimes()
            if level1_components:
                self._detected_installations['level1_system_runtimes'] = level1_components
                self.logger.info(f"Nível 1 - Runtimes do Sistema: {level1_components.component_count} componentes detectados")
            
            # Nível 2: Dependências EmuDeck
            level2_components = self._detect_level2_emudeck_dependencies()
            if level2_components:
                self._detected_installations['level2_emudeck_dependencies'] = level2_components
                self.logger.info(f"Nível 2 - Dependências EmuDeck: {level2_components.component_count} componentes detectados")
            
            # Nível 3: Frontend/Backend
            level3_components = self._detect_level3_frontend_backend()
            if level3_components:
                self._detected_installations['level3_frontend_backend'] = level3_components
                self.logger.info(f"Nível 3 - Frontend/Backend: {level3_components.component_count} componentes detectados")
            
            # Nível 4: Emuladores
            level4_components = self._detect_level4_emulator_dependencies()
            if level4_components:
                self._detected_installations['level4_emulator_dependencies'] = level4_components
                self.logger.info(f"Nível 4 - Emuladores: {level4_components.component_count} componentes detectados")
            
            # Atualizar timestamp
            self._last_scan_time = datetime.now()
            
            # Log dos resultados
            if self._detected_installations:
                self.logger.info(f"Scan concluído. {len(self._detected_installations)} instalações legadas detectadas:")
                for key, installation in self._detected_installations.items():
                    size_mb = installation.size_bytes / (1024 * 1024)
                    self.logger.info(f"  - {installation.name}: {installation.path} ({size_mb:.1f} MB)")
            else:
                self.logger.info("Scan concluído. Nenhuma instalação legada detectada.")
            
            return self._detected_installations.copy()
            
        except Exception as e:
            self.logger.error(f"Erro durante scan de instalações legadas: {e}")
            return {}
        finally:
            self._scan_in_progress = False
    
    def get_detected_installations(self, force_rescan: bool = False) -> Dict[str, Dict[str, Any]]:
        """Obtém lista de instalações legadas detectadas.
        
        Args:
            force_rescan: Força novo scan
            
        Returns:
            Dicionário com instalações detectadas em formato de dicionário
        """
        installations = self.scan_for_legacy_installations(force_rescan)
        return {key: installation.to_dict() for key, installation in installations.items()}
    
    def has_legacy_installations(self) -> bool:
        """Verifica se há instalações legadas detectadas.
        
        Returns:
            True se há instalações legadas, False caso contrário
        """
        installations = self.scan_for_legacy_installations()
        return len(installations) > 0
    
    def get_installation_by_type(self, installation_type: str) -> Optional[Dict[str, Any]]:
        """Obtém instalação específica por tipo.
        
        Args:
            installation_type: Tipo da instalação (emudeck, es-de)
            
        Returns:
            Dicionário com informações da instalação ou None se não encontrada
        """
        installations = self.scan_for_legacy_installations()
        installation = installations.get(installation_type)
        return installation.to_dict() if installation else None
    
    def get_total_legacy_size(self) -> int:
        """Calcula o tamanho total de todas as instalações legadas.
        
        Returns:
            Tamanho total em bytes
        """
        installations = self.scan_for_legacy_installations()
        total_size = sum(installation.size_bytes for installation in installations.values())
        return total_size
    
    def get_cleanup_recommendations(self) -> List[Dict[str, Any]]:
        """Gera recomendações para limpeza de instalações legadas categorizadas por nível hierárquico.
        
        Returns:
            Lista de recomendações organizadas por nível de dependência
        """
        recommendations = []
        installations = self.scan_for_legacy_installations()
        
        if not installations:
            return [{
                'type': 'info',
                'title': 'Nenhuma instalação legada detectada',
                'description': 'Não foram encontradas instalações legadas do EmuDeck ou EmulationStation-DE.',
                'action': 'none'
            }]
        
        total_size_mb = self.get_total_legacy_size() / (1024 * 1024)
        
        # Recomendação geral
        recommendations.append({
            'type': 'warning',
            'title': f'Ecossistema EmuDeck detectado ({total_size_mb:.1f} MB)',
            'description': f'Foram encontrados componentes do ecossistema EmuDeck em {len(installations.keys())} categorias que podem ser migradas ou removidas.',
            'action': 'review'
        })
        
        # Recomendações por nível hierárquico
        level_descriptions = {
            'emudeck': {
                'title': 'EmuDeck Principal',
                'description': 'Ferramenta de gerenciamento principal do EmuDeck',
                'priority': 'high',
                'impact': 'Remoção afetará todo o ecossistema EmuDeck'
            },
            'es-de': {
                'title': 'EmulationStation-DE',
                'description': 'Frontend gráfico para navegação de jogos',
                'priority': 'high',
                'impact': 'Remoção afetará a interface de usuário'
            },
            'level1_system_runtimes': {
                'title': 'Nível 1 - Runtimes do Sistema',
                'description': 'Componentes fundamentais do Windows (Visual C++, .NET, DirectX)',
                'priority': 'critical',
                'impact': 'CUIDADO: Remoção pode afetar outros programas do sistema'
            },
            'level2_emudeck_dependencies': {
                'title': 'Nível 2 - Dependências EmuDeck',
                'description': 'Ferramentas específicas do EmuDeck (Git, 7-Zip, PowerShell)',
                'priority': 'medium',
                'impact': 'Remoção afetará atualizações e instalação do EmuDeck'
            },
            'level3_frontend_backend': {
                'title': 'Nível 3 - Frontend/Backend',
                'description': 'Bibliotecas de interface e Steam (SDL2, Boost, cURL, etc.)',
                'priority': 'medium',
                'impact': 'Remoção afetará funcionalidade de jogos e interface'
            },
            'level4_emulator_dependencies': {
                'title': 'Nível 4 - Emuladores',
                'description': 'Emuladores individuais (RetroArch, PCSX2, Dolphin, etc.)',
                'priority': 'low',
                'impact': 'Remoção afetará apenas os emuladores específicos'
            }
        }
        
        # Recomendações específicas por categoria
        for installation_type, installation in installations.items():
            if installation_type in level_descriptions:
                level_info = level_descriptions[installation_type]
                
                # Verificar se é um objeto LegacyInstallation
                if hasattr(installation, 'size_bytes'):
                    size_mb = installation.size_bytes / (1024 * 1024)
                    size_info = f" ({size_mb:.1f} MB)"
                    
                    # Para instalações hierárquicas, mostrar contagem de componentes
                    if hasattr(installation, 'component_count'):
                        size_info = f" ({installation.component_count} componentes, {size_mb:.1f} MB)"
                else:
                    # Fallback para outros tipos
                    size_info = " (detectado)"
                
                recommendations.append({
                    'type': 'action',
                    'title': level_info['title'] + size_info,
                    'description': f"{level_info['description']}. {level_info['impact']}",
                    'action': 'migrate' if level_info['priority'] != 'critical' else 'review_carefully',
                    'priority': level_info['priority'],
                    'installation_type': installation_type,
                    'path': getattr(installation, 'path', 'Múltiplos locais'),
                    'size_bytes': getattr(installation, 'size_bytes', 0),
                    'impact_warning': level_info['impact']
                })
        
        # Adicionar recomendação de ordem de remoção
        if len(installations.keys()) > 1:
            recommendations.append({
                'type': 'info',
                'title': 'Ordem Recomendada de Remoção',
                'description': 'Para remoção segura: 1) Nível 4 (Emuladores), 2) Nível 3 (Frontend/Backend), '
                             '3) Nível 2 (Dependências EmuDeck), 4) EmuDeck/ES-DE principais. '
                             'NUNCA remova Nível 1 (Runtimes) sem verificação cuidadosa.',
                'action': 'guidance'
            })
        
        return recommendations

    def get_detailed_component_report(self) -> Dict[str, Any]:
        """Gera relatório detalhado dos componentes detectados em cada nível.
        
        Returns:
            Dicionário com informações detalhadas dos componentes por nível
        """
        report = {
            'summary': {
                'total_installations': 0,
                'total_components': 0,
                'total_size_mb': 0.0
            },
            'levels': {}
        }
        
        installations = self.scan_for_legacy_installations()
        
        if not installations:
            return report
    
    def _validate_es_de_path_resolution(self, es_de_path: str) -> Dict[str, Any]:
        """Valida a resolução de caminhos relativos do ES-DE.
        
        Args:
            es_de_path: Caminho da instalação do ES-DE
            
        Returns:
            Dict com resultados da validação
        """
        validation_result = {
            'es_find_rules_found': False,
            'es_find_rules_path': None,
            'espath_variables': [],
            'path_resolution_tests': [],
            'validation_status': 'failed'
        }
        
        try:
            # Procurar por es_find_rules.xml
            es_find_rules_path = os.path.join(es_de_path, 'es_find_rules.xml')
            if PathUtils.exists(es_find_rules_path):
                validation_result['es_find_rules_found'] = True
                validation_result['es_find_rules_path'] = es_find_rules_path
                
                # Tentar ler e analisar o arquivo
                try:
                    content = FileUtils.read_file(es_find_rules_path)
                    validation_result['espath_variables'] = self._extract_espath_variables(content)
                    validation_result['path_resolution_tests'] = self._test_path_resolution(
                        es_de_path, validation_result['espath_variables']
                    )
                except Exception as e:
                    self.logger.warning(f"Erro ao analisar es_find_rules.xml: {e}")
            
            # Determinar status da validação
            if validation_result['es_find_rules_found']:
                if validation_result['path_resolution_tests']:
                    successful_tests = sum(1 for test in validation_result['path_resolution_tests'] 
                                         if test.get('success', False))
                    total_tests = len(validation_result['path_resolution_tests'])
                    if successful_tests == total_tests:
                        validation_result['validation_status'] = 'passed'
                    elif successful_tests > 0:
                        validation_result['validation_status'] = 'partial'
                else:
                    validation_result['validation_status'] = 'no_tests'
            
        except Exception as e:
            self.logger.error(f"Erro na validação de resolução de caminhos ES-DE: {e}")
        
        return validation_result
    
    def _extract_espath_variables(self, xml_content: str) -> List[Dict[str, str]]:
        """Extrai variáveis %ESPATH% do conteúdo XML.
        
        Args:
            xml_content: Conteúdo do arquivo es_find_rules.xml
            
        Returns:
            Lista de variáveis encontradas
        """
        variables = []
        
        try:
            # Buscar por padrões %ESPATH% no XML
            import re
            espath_pattern = r'%ESPATH%([^%\s<>"]*)'
            matches = re.findall(espath_pattern, xml_content)
            
            for match in matches:
                variables.append({
                    'pattern': f'%ESPATH%{match}',
                    'relative_path': match,
                    'type': 'espath_variable'
                })
            
            # Buscar também por caminhos relativos comuns
            relative_patterns = [
                r'\.\.[\\/]([^<>"]*)',  # Caminhos com ../
                r'\.[\\/]([^<>"]*)'     # Caminhos com ./
            ]
            
            for pattern in relative_patterns:
                matches = re.findall(pattern, xml_content)
                for match in matches:
                    variables.append({
                        'pattern': match,
                        'relative_path': match,
                        'type': 'relative_path'
                    })
                    
        except Exception as e:
            self.logger.error(f"Erro ao extrair variáveis ESPATH: {e}")
        
        return variables
    
    def _test_path_resolution(self, es_de_path: str, variables: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Testa a resolução de caminhos relativos.
        
        Args:
            es_de_path: Caminho base do ES-DE
            variables: Lista de variáveis para testar
            
        Returns:
            Lista de resultados dos testes
        """
        test_results = []
        
        try:
            for var in variables:
                test_result = {
                    'variable': var['pattern'],
                    'relative_path': var['relative_path'],
                    'type': var['type'],
                    'success': False,
                    'resolved_path': None,
                    'target_exists': False
                }
                
                try:
                    # Resolver caminho baseado no tipo
                    if var['type'] == 'espath_variable':
                        # %ESPATH% aponta para o diretório do ES-DE
                        resolved_path = os.path.join(es_de_path, var['relative_path'].lstrip('/\\'))
                    else:
                        # Caminho relativo normal
                        resolved_path = os.path.normpath(os.path.join(es_de_path, var['relative_path']))
                    
                    test_result['resolved_path'] = resolved_path
                    test_result['target_exists'] = PathUtils.exists(resolved_path)
                    test_result['success'] = True
                    
                except Exception as e:
                    test_result['error'] = str(e)
                
                test_results.append(test_result)
                
        except Exception as e:
            self.logger.error(f"Erro nos testes de resolução de caminhos: {e}")
        
        return test_results
    
    def _validate_bifurcated_structure(self, emudeck_path: str, appdata_path: str) -> Dict[str, Any]:
        """Valida a estrutura bifurcada EmuDeck (AppData ↔ Emulation).
        
        Args:
            emudeck_path: Caminho principal do EmuDeck
            appdata_path: Caminho do AppData do EmuDeck
            
        Returns:
            Dict com resultados da validação
        """
        validation_result = {
            'structure_valid': False,
            'appdata_config_found': False,
            'emulation_dir_found': False,
            'config_references_valid': False,
            'cross_references': [],
            'validation_status': 'failed'
        }
        
        try:
            # Verificar se AppData existe
            if PathUtils.exists(appdata_path):
                validation_result['appdata_config_found'] = True
                
                # Procurar por arquivos de configuração no AppData
                config_files = ['config.json', 'settings.json', 'emudeck.json']
                for config_file in config_files:
                    config_path = os.path.join(appdata_path, config_file)
                    if PathUtils.exists(config_path):
                        try:
                            # Analisar referências ao diretório Emulation
                            content = FileUtils.read_file(config_path)
                            references = self._find_emulation_references(content, emudeck_path)
                            validation_result['cross_references'].extend(references)
                        except Exception as e:
                            self.logger.warning(f"Erro ao analisar {config_file}: {e}")
            
            # Verificar se diretório Emulation existe
            if PathUtils.exists(emudeck_path):
                validation_result['emulation_dir_found'] = True
            
            # Validar referências cruzadas
            valid_references = sum(1 for ref in validation_result['cross_references'] 
                                 if ref.get('target_exists', False))
            total_references = len(validation_result['cross_references'])
            
            if total_references > 0:
                validation_result['config_references_valid'] = valid_references == total_references
            
            # Determinar status geral
            if (validation_result['appdata_config_found'] and 
                validation_result['emulation_dir_found'] and
                validation_result['config_references_valid']):
                validation_result['structure_valid'] = True
                validation_result['validation_status'] = 'passed'
            elif validation_result['appdata_config_found'] or validation_result['emulation_dir_found']:
                validation_result['validation_status'] = 'partial'
                
        except Exception as e:
            self.logger.error(f"Erro na validação de estrutura bifurcada: {e}")
        
        return validation_result
    
    def _find_emulation_references(self, content: str, emudeck_path: str) -> List[Dict[str, Any]]:
        """Encontra referências ao diretório Emulation no conteúdo.
        
        Args:
            content: Conteúdo do arquivo de configuração
            emudeck_path: Caminho do diretório Emulation
            
        Returns:
            Lista de referências encontradas
        """
        references = []
        
        try:
            import re
            
            # Padrões para encontrar caminhos
            path_patterns = [
                r'"([^"]*[Ee]mulation[^"]*)"',  # Caminhos entre aspas
                r"'([^']*[Ee]mulation[^']*)'",  # Caminhos entre aspas simples
                r'([A-Za-z]:\\[^\\s]*[Ee]mulation[^\\s]*)',  # Caminhos absolutos Windows
            ]
            
            for pattern in path_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    reference = {
                        'found_path': match,
                        'target_exists': PathUtils.exists(match),
                        'matches_expected': os.path.normpath(match) == os.path.normpath(emudeck_path)
                    }
                    references.append(reference)
                    
        except Exception as e:
            self.logger.error(f"Erro ao encontrar referências de emulação: {e}")
        
        return references
    
    def _test_emulator_path_resolution(self, es_de_path: str) -> Dict[str, Any]:
        """Testa resolução de caminhos de emuladores como o ES-DE faria.
        
        Args:
            es_de_path: Caminho da instalação do ES-DE
            
        Returns:
            Dict com resultados dos testes
        """
        test_result = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'test_details': [],
            'validation_status': 'failed'
        }
        
        try:
            # Caminhos de emuladores comuns para testar
            test_emulator_paths = [
                '..\\Emulators\\xenia\\xenia.exe',
                '..\\Emulators\\RetroArch\\retroarch.exe',
                '..\\Emulators\\PCSX2\\pcsx2.exe',
                '..\\Emulators\\Dolphin\\Dolphin.exe',
                '..\\Emulators\\RPCS3\\rpcs3.exe'
            ]
            
            for emulator_path in test_emulator_paths:
                test_detail = {
                    'relative_path': emulator_path,
                    'resolved_path': None,
                    'exists': False,
                    'success': False
                }
                
                try:
                    # Resolver caminho relativo a partir do ES-DE
                    resolved_path = os.path.normpath(os.path.join(es_de_path, emulator_path))
                    test_detail['resolved_path'] = resolved_path
                    test_detail['exists'] = PathUtils.exists(resolved_path)
                    test_detail['success'] = test_detail['exists']
                    
                    if test_detail['success']:
                        test_result['successful_tests'] += 1
                    else:
                        test_result['failed_tests'] += 1
                        
                except Exception as e:
                    test_detail['error'] = str(e)
                    test_result['failed_tests'] += 1
                
                test_result['test_details'].append(test_detail)
                test_result['total_tests'] += 1
            
            # Determinar status da validação
            if test_result['successful_tests'] == test_result['total_tests']:
                test_result['validation_status'] = 'passed'
            elif test_result['successful_tests'] > 0:
                test_result['validation_status'] = 'partial'
                
        except Exception as e:
            self.logger.error(f"Erro no teste de resolução de caminhos de emuladores: {e}")
        
        return test_result
        
        total_size_bytes = 0
        total_components = 0
        
        for installation_type, installation in installations.items():
            if hasattr(installation, 'components') and hasattr(installation, 'level'):
                level_key = f"level_{installation.level}"
                
                if level_key not in report['levels']:
                    report['levels'][level_key] = {
                        'name': installation.name,
                        'total_components': 0,
                        'size_mb': 0.0,
                        'components': []
                    }
                
                # Adicionar informações do nível
                report['levels'][level_key]['total_components'] = installation.component_count
                report['levels'][level_key]['size_mb'] = installation.size_bytes / (1024 * 1024)
                
                # Adicionar componentes específicos
                for component in installation.components:
                    component_info = {
                        'name': component.get('name', 'Componente desconhecido'),
                        'status': component.get('status', 'unknown'),
                        'category': component.get('category', 'unknown'),
                        'path': component.get('path', 'N/A')
                    }
                    
                    # Adicionar informações específicas se disponíveis
                    if 'versions' in component:
                        component_info['versions'] = component['versions']
                    if 'registry' in component:
                        component_info['registry'] = component['registry']
                    if 'files' in component:
                        component_info['files'] = component['files']
                    
                    report['levels'][level_key]['components'].append(component_info)
                
                total_size_bytes += installation.size_bytes
                total_components += installation.component_count
            
            elif hasattr(installation, 'name'):
                # Instalação principal (EmuDeck/ES-DE)
                main_key = installation_type
                report['levels'][main_key] = {
                    'name': installation.name,
                    'path': installation.path,
                    'version': installation.version,
                    'size_mb': installation.size_bytes / (1024 * 1024),
                    'type': installation.installation_type
                }
                
                total_size_bytes += installation.size_bytes
                total_components += 1
        
        # Atualizar resumo
        report['summary']['total_installations'] = len(installations)
        report['summary']['total_components'] = total_components
        report['summary']['total_size_mb'] = total_size_bytes / (1024 * 1024)
        
        return report