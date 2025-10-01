"""
Configuration Service

Serviço responsável pelo gerenciamento de configurações do sistema,
seguindo os requisitos RF009 do DRS FrontEmu-Tools.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

from sd_emulation_gui.utils.base_service import BaseService
from sd_emulation_gui.utils.file_utils import FileUtils
from sd_emulation_gui.utils.path_utils import PathUtils


class ConfigurationTemplate:
    """Template de configuração para emuladores."""
    
    def __init__(self, name: str, emulator: str, platform: str, 
                 config_data: Dict[str, Any], description: str = ""):
        """Inicializa um template de configuração.
        
        Args:
            name: Nome do template
            emulator: Nome do emulador
            platform: Plataforma alvo
            config_data: Dados de configuração
            description: Descrição do template
        """
        self.name = name
        self.emulator = emulator
        self.platform = platform
        self.config_data = config_data
        self.description = description
        self.created_at = datetime.now()
        self.version = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte template para dicionário."""
        return {
            'name': self.name,
            'emulator': self.emulator,
            'platform': self.platform,
            'config_data': self.config_data,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigurationTemplate':
        """Cria template a partir de dicionário."""
        template = cls(
            name=data['name'],
            emulator=data['emulator'],
            platform=data['platform'],
            config_data=data['config_data'],
            description=data.get('description', '')
        )
        
        if 'created_at' in data:
            template.created_at = datetime.fromisoformat(data['created_at'])
        if 'version' in data:
            template.version = data['version']
            
        return template


class ConfigurationBackup:
    """Backup de configuração."""
    
    def __init__(self, name: str, config_path: str, backup_data: Dict[str, Any]):
        """Inicializa backup de configuração.
        
        Args:
            name: Nome do backup
            config_path: Caminho da configuração original
            backup_data: Dados do backup
        """
        self.name = name
        self.config_path = config_path
        self.backup_data = backup_data
        self.created_at = datetime.now()
        self.size = len(json.dumps(backup_data))
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte backup para dicionário."""
        return {
            'name': self.name,
            'config_path': self.config_path,
            'backup_data': self.backup_data,
            'created_at': self.created_at.isoformat(),
            'size': self.size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigurationBackup':
        """Cria backup a partir de dicionário."""
        backup = cls(
            name=data['name'],
            config_path=data['config_path'],
            backup_data=data['backup_data']
        )
        
        if 'created_at' in data:
            backup.created_at = datetime.fromisoformat(data['created_at'])
        if 'size' in data:
            backup.size = data['size']
            
        return backup


class ConfigurationService(BaseService):
    """Serviço para gerenciamento de configurações de emuladores."""
    
    def __init__(self, config_base_path: Optional[str] = None):
        """Inicializa o serviço de configuração.
        
        Args:
            config_base_path: Caminho base para configurações
        """
        # Configurar caminhos
        if config_base_path:
            self.config_base_path = Path(config_base_path)
        else:
            self.config_base_path = Path.cwd() / "config"
        
        self.templates_path = self.config_base_path / "templates"
        self.backups_path = self.config_base_path / "backups"
        self.profiles_path = self.config_base_path / "profiles"
        
        # Cache de templates e backups
        self._templates_cache: Dict[str, ConfigurationTemplate] = {}
        self._backups_cache: Dict[str, ConfigurationBackup] = {}
        
        # Configurações
        self.max_backups_per_config = 10
        self.auto_backup_enabled = True
        
        super().__init__()
        
    def initialize(self) -> None:
        """Inicializa o serviço de configuração."""
        try:
            self.logger.info("Inicializando ConfigurationService...")
            
            # Criar diretórios necessários
            self._create_directories()
            
            # Carregar templates e backups
            self._load_templates()
            self._load_backups()
            
            # Criar templates padrão se não existirem
            self._create_default_templates()
            
            self.logger.info(f"ConfigurationService inicializado. "
                           f"{len(self._templates_cache)} templates, "
                           f"{len(self._backups_cache)} backups")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar ConfigurationService: {e}")
            raise
    
    def get_configuration(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Obtém configuração de um arquivo.
        
        Args:
            config_path: Caminho do arquivo de configuração
            
        Returns:
            Dados de configuração ou None se não encontrado
        """
        try:
            config_file = Path(config_path)
            
            if not config_file.exists():
                self.logger.warning(f"Arquivo de configuração não encontrado: {config_path}")
                return None
            
            # Determinar formato do arquivo
            if config_file.suffix.lower() == '.json':
                return self._load_json_config(config_file)
            elif config_file.suffix.lower() in ['.ini', '.cfg']:
                return self._load_ini_config(config_file)
            elif config_file.suffix.lower() in ['.xml']:
                return self._load_xml_config(config_file)
            else:
                # Tentar como texto simples
                return self._load_text_config(config_file)
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração {config_path}: {e}")
            return None
    
    def save_configuration(self, config_path: str, config_data: Dict[str, Any], 
                          create_backup: bool = True) -> bool:
        """Salva configuração em arquivo.
        
        Args:
            config_path: Caminho do arquivo de configuração
            config_data: Dados de configuração
            create_backup: Se deve criar backup antes de salvar
            
        Returns:
            True se salvou com sucesso
        """
        try:
            config_file = Path(config_path)
            
            # Criar backup se solicitado e arquivo existe
            if create_backup and config_file.exists() and self.auto_backup_enabled:
                self.create_backup(config_path)
            
            # Criar diretório pai se não existir
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Determinar formato e salvar
            if config_file.suffix.lower() == '.json':
                return self._save_json_config(config_file, config_data)
            elif config_file.suffix.lower() in ['.ini', '.cfg']:
                return self._save_ini_config(config_file, config_data)
            elif config_file.suffix.lower() in ['.xml']:
                return self._save_xml_config(config_file, config_data)
            else:
                # Salvar como JSON por padrão
                return self._save_json_config(config_file, config_data)
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração {config_path}: {e}")
            return False
    
    def apply_template(self, template_name: str, config_path: str, 
                      variables: Optional[Dict[str, Any]] = None) -> bool:
        """Aplica template de configuração a um arquivo.
        
        Args:
            template_name: Nome do template
            config_path: Caminho do arquivo de configuração
            variables: Variáveis para substituição no template
            
        Returns:
            True se aplicou com sucesso
        """
        try:
            template = self._templates_cache.get(template_name)
            if not template:
                self.logger.error(f"Template não encontrado: {template_name}")
                return False
            
            # Copiar dados do template
            config_data = template.config_data.copy()
            
            # Aplicar variáveis se fornecidas
            if variables:
                config_data = self._apply_variables(config_data, variables)
            
            # Salvar configuração
            return self.save_configuration(config_path, config_data)
            
        except Exception as e:
            self.logger.error(f"Erro ao aplicar template {template_name}: {e}")
            return False
    
    def create_template(self, name: str, emulator: str, platform: str,
                       config_path: str, description: str = "") -> bool:
        """Cria template a partir de configuração existente.
        
        Args:
            name: Nome do template
            emulator: Nome do emulador
            platform: Plataforma alvo
            config_path: Caminho da configuração base
            description: Descrição do template
            
        Returns:
            True se criou com sucesso
        """
        try:
            # Carregar configuração existente
            config_data = self.get_configuration(config_path)
            if not config_data:
                self.logger.error(f"Não foi possível carregar configuração: {config_path}")
                return False
            
            # Criar template
            template = ConfigurationTemplate(
                name=name,
                emulator=emulator,
                platform=platform,
                config_data=config_data,
                description=description
            )
            
            # Salvar template
            template_file = self.templates_path / f"{name}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Adicionar ao cache
            self._templates_cache[name] = template
            
            self.logger.info(f"Template criado: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao criar template {name}: {e}")
            return False
    
    def get_templates(self, emulator: Optional[str] = None, 
                     platform: Optional[str] = None) -> List[ConfigurationTemplate]:
        """Obtém lista de templates disponíveis.
        
        Args:
            emulator: Filtrar por emulador (opcional)
            platform: Filtrar por plataforma (opcional)
            
        Returns:
            Lista de templates
        """
        templates = list(self._templates_cache.values())
        
        # Aplicar filtros
        if emulator:
            templates = [t for t in templates if t.emulator.lower() == emulator.lower()]
        
        if platform:
            templates = [t for t in templates if t.platform.lower() == platform.lower()]
        
        # Ordenar por nome
        templates.sort(key=lambda t: t.name)
        
        return templates
    
    def create_backup(self, config_path: str, backup_name: Optional[str] = None) -> bool:
        """Cria backup de configuração.
        
        Args:
            config_path: Caminho da configuração
            backup_name: Nome do backup (opcional, usa timestamp se None)
            
        Returns:
            True se criou backup com sucesso
        """
        try:
            config_data = self.get_configuration(config_path)
            if not config_data:
                self.logger.error(f"Não foi possível carregar configuração para backup: {config_path}")
                return False
            
            # Gerar nome do backup se não fornecido
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                config_name = Path(config_path).stem
                backup_name = f"{config_name}_{timestamp}"
            
            # Criar backup
            backup = ConfigurationBackup(
                name=backup_name,
                config_path=config_path,
                backup_data=config_data
            )
            
            # Salvar backup
            backup_file = self.backups_path / f"{backup_name}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Adicionar ao cache
            self._backups_cache[backup_name] = backup
            
            # Limpar backups antigos se necessário
            self._cleanup_old_backups(config_path)
            
            self.logger.info(f"Backup criado: {backup_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return False
    
    def restore_backup(self, backup_name: str, config_path: Optional[str] = None) -> bool:
        """Restaura backup de configuração.
        
        Args:
            backup_name: Nome do backup
            config_path: Caminho de destino (usa original se None)
            
        Returns:
            True se restaurou com sucesso
        """
        try:
            backup = self._backups_cache.get(backup_name)
            if not backup:
                self.logger.error(f"Backup não encontrado: {backup_name}")
                return False
            
            # Usar caminho original se não especificado
            if not config_path:
                config_path = backup.config_path
            
            # Restaurar configuração
            return self.save_configuration(config_path, backup.backup_data, create_backup=False)
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar backup {backup_name}: {e}")
            return False
    
    def get_backups(self, config_path: Optional[str] = None) -> List[ConfigurationBackup]:
        """Obtém lista de backups disponíveis.
        
        Args:
            config_path: Filtrar por caminho de configuração (opcional)
            
        Returns:
            Lista de backups
        """
        backups = list(self._backups_cache.values())
        
        # Filtrar por caminho se especificado
        if config_path:
            backups = [b for b in backups if b.config_path == config_path]
        
        # Ordenar por data (mais recente primeiro)
        backups.sort(key=lambda b: b.created_at, reverse=True)
        
        return backups
    
    def validate_configuration(self, config_path: str, 
                             schema: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
        """Valida configuração contra esquema.
        
        Args:
            config_path: Caminho da configuração
            schema: Esquema de validação (opcional)
            
        Returns:
            Tupla (é_válido, lista_de_erros)
        """
        try:
            config_data = self.get_configuration(config_path)
            if not config_data:
                return False, ["Não foi possível carregar configuração"]
            
            errors = []
            
            # Validação básica
            if not isinstance(config_data, dict):
                errors.append("Configuração deve ser um objeto/dicionário")
                return False, errors
            
            # Validação contra esquema se fornecido
            if schema:
                errors.extend(self._validate_against_schema(config_data, schema))
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Erro ao validar configuração {config_path}: {e}")
            return False, [str(e)]
    
    def _create_directories(self) -> None:
        """Cria diretórios necessários."""
        for path in [self.config_base_path, self.templates_path, 
                    self.backups_path, self.profiles_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def _load_templates(self) -> None:
        """Carrega templates do disco."""
        try:
            for template_file in self.templates_path.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    template = ConfigurationTemplate.from_dict(data)
                    self._templates_cache[template.name] = template
                    
                except Exception as e:
                    self.logger.warning(f"Erro ao carregar template {template_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao carregar templates: {e}")
    
    def _load_backups(self) -> None:
        """Carrega backups do disco."""
        try:
            for backup_file in self.backups_path.glob("*.json"):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    backup = ConfigurationBackup.from_dict(data)
                    self._backups_cache[backup.name] = backup
                    
                except Exception as e:
                    self.logger.warning(f"Erro ao carregar backup {backup_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao carregar backups: {e}")
    
    def _create_default_templates(self) -> None:
        """Cria templates padrão se não existirem."""
        default_templates = [
            {
                'name': 'RetroArch_Default',
                'emulator': 'RetroArch',
                'platform': 'Multi',
                'description': 'Configuração padrão do RetroArch',
                'config_data': {
                    'video_driver': 'gl',
                    'audio_driver': 'dsound',
                    'input_driver': 'dinput',
                    'video_fullscreen': 'false',
                    'video_windowed_fullscreen': 'true',
                    'video_smooth': 'true',
                    'audio_enable': 'true',
                    'savestate_auto_save': 'true',
                    'savestate_auto_load': 'true'
                }
            },
            {
                'name': 'PCSX2_Performance',
                'emulator': 'PCSX2',
                'platform': 'PlayStation 2',
                'description': 'Configuração otimizada para performance',
                'config_data': {
                    'EmuCore/GS/Renderer': '11',  # OpenGL
                    'EmuCore/GS/upscale_multiplier': '1',
                    'EmuCore/Speedhacks/EECycleRate': '0',
                    'EmuCore/Speedhacks/VUCycleSteal': '0',
                    'EmuCore/EnableWideScreenPatches': 'false',
                    'EmuCore/EnableCheats': 'false'
                }
            }
        ]
        
        for template_data in default_templates:
            if template_data['name'] not in self._templates_cache:
                template = ConfigurationTemplate(
                    name=template_data['name'],
                    emulator=template_data['emulator'],
                    platform=template_data['platform'],
                    config_data=template_data['config_data'],
                    description=template_data['description']
                )
                
                # Salvar template
                template_file = self.templates_path / f"{template.name}.json"
                with open(template_file, 'w', encoding='utf-8') as f:
                    json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
                
                self._templates_cache[template.name] = template
    
    def _load_json_config(self, config_file: Path) -> Dict[str, Any]:
        """Carrega configuração JSON."""
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_json_config(self, config_file: Path, config_data: Dict[str, Any]) -> bool:
        """Salva configuração JSON."""
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    
    def _load_ini_config(self, config_file: Path) -> Dict[str, Any]:
        """Carrega configuração INI."""
        import configparser
        
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        
        result = {}
        for section_name in config.sections():
            result[section_name] = dict(config[section_name])
        
        return result
    
    def _save_ini_config(self, config_file: Path, config_data: Dict[str, Any]) -> bool:
        """Salva configuração INI."""
        import configparser
        
        config = configparser.ConfigParser()
        
        for section_name, section_data in config_data.items():
            config[section_name] = section_data
        
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)
        
        return True
    
    def _load_xml_config(self, config_file: Path) -> Dict[str, Any]:
        """Carrega configuração XML."""
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(config_file)
        root = tree.getroot()
        
        def xml_to_dict(element):
            result = {}
            for child in element:
                if len(child) == 0:
                    result[child.tag] = child.text
                else:
                    result[child.tag] = xml_to_dict(child)
            return result
        
        return {root.tag: xml_to_dict(root)}
    
    def _save_xml_config(self, config_file: Path, config_data: Dict[str, Any]) -> bool:
        """Salva configuração XML."""
        import xml.etree.ElementTree as ET
        
        def dict_to_xml(data, parent=None):
            if parent is None:
                root_key = list(data.keys())[0]
                root = ET.Element(root_key)
                dict_to_xml(data[root_key], root)
                return root
            
            for key, value in data.items():
                if isinstance(value, dict):
                    child = ET.SubElement(parent, key)
                    dict_to_xml(value, child)
                else:
                    child = ET.SubElement(parent, key)
                    child.text = str(value)
        
        root = dict_to_xml(config_data)
        tree = ET.ElementTree(root)
        tree.write(config_file, encoding='utf-8', xml_declaration=True)
        
        return True
    
    def _load_text_config(self, config_file: Path) -> Dict[str, Any]:
        """Carrega configuração de texto simples."""
        result = {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        result[key.strip()] = value.strip()
                    else:
                        result[f'line_{line_num}'] = line
        
        return result
    
    def _apply_variables(self, config_data: Dict[str, Any], 
                        variables: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica variáveis aos dados de configuração."""
        def replace_variables(obj):
            if isinstance(obj, str):
                for var_name, var_value in variables.items():
                    obj = obj.replace(f"{{{var_name}}}", str(var_value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_variables(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_variables(item) for item in obj]
            else:
                return obj
        
        return replace_variables(config_data)
    
    def _validate_against_schema(self, config_data: Dict[str, Any], 
                                schema: Dict[str, Any]) -> List[str]:
        """Valida configuração contra esquema."""
        errors = []
        
        # Implementação básica de validação
        # Em um sistema real, usaria jsonschema ou similar
        
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Campo obrigatório ausente: {field}")
        
        return errors
    
    def _cleanup_old_backups(self, config_path: str) -> None:
        """Remove backups antigos se exceder o limite."""
        try:
            config_backups = [b for b in self._backups_cache.values() 
                            if b.config_path == config_path]
            
            if len(config_backups) > self.max_backups_per_config:
                # Ordenar por data (mais antigo primeiro)
                config_backups.sort(key=lambda b: b.created_at)
                
                # Remover backups mais antigos
                to_remove = config_backups[:-self.max_backups_per_config]
                
                for backup in to_remove:
                    backup_file = self.backups_path / f"{backup.name}.json"
                    if backup_file.exists():
                        backup_file.unlink()
                    
                    if backup.name in self._backups_cache:
                        del self._backups_cache[backup.name]
                
                self.logger.info(f"Removidos {len(to_remove)} backups antigos para {config_path}")
                
        except Exception as e:
            self.logger.error(f"Erro ao limpar backups antigos: {e}")