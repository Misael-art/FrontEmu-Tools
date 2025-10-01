#!/usr/bin/env python3
"""
Script de Configuração do Sistema de Visão Histórica
Inicializa e configura o sistema de visão histórica do SD Emulation GUI.

Autor: Sistema de Visão Histórica
Data: 2024
"""

import os
import sys
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from history.database_manager import DatabaseManager
    from history.history_manager import HistoryManager
    from history.config_manager import ConfigManager
except ImportError as e:
    print(f"⚠️ Erro ao importar módulos do sistema histórico: {e}")
    sys.exit(1)


class HistorySystemSetup:
    """
    Classe responsável pela configuração inicial do sistema de visão histórica.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa o configurador do sistema histórico.
        
        Args:
            base_path: Caminho base do projeto (opcional)
        """
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.history_data_path = self.base_path / "history_data"
        self.config_path = self.base_path / "config"
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """
        Configura o sistema de logging.
        
        Returns:
            Logger configurado
        """
        logger = logging.getLogger('history_setup')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def create_directory_structure(self) -> bool:
        """
        Cria a estrutura de diretórios necessária.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            directories = [
                self.history_data_path,
                self.history_data_path / "databases",
                self.history_data_path / "backups",
                self.history_data_path / "reports",
                self.history_data_path / "templates",
                self.history_data_path / "logs",
                self.config_path
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"✅ Diretório criado/verificado: {directory}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar estrutura de diretórios: {e}")
            return False
    
    def create_default_config(self) -> bool:
        """
        Cria arquivos de configuração padrão.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            # Configuração principal do sistema histórico
            history_config = {
                "database": {
                    "path": "history_data/databases/history.db",
                    "backup_interval": 3600,
                    "max_backup_files": 10,
                    "connection_timeout": 30
                },
                "metrics": {
                    "collection_interval": 60,
                    "retention_days": 30,
                    "thresholds": {
                        "cpu_percent": 80.0,
                        "memory_percent": 85.0,
                        "disk_usage_percent": 90.0
                    }
                },
                "reports": {
                    "output_directory": "history_data/reports",
                    "template_directory": "history_data/templates",
                    "auto_generate": True,
                    "schedule": {
                        "daily": "06:00",
                        "weekly": "Sunday 07:00",
                        "monthly": "1st 08:00"
                    }
                },
                "logging": {
                    "level": "INFO",
                    "file": "history_data/logs/history_system.log",
                    "max_size": "10MB",
                    "backup_count": 5
                }
            }
            
            config_file = self.config_path / "history_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(history_config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Configuração principal criada: {config_file}")
            
            # Configuração de integração
            integration_config = {
                "validation_service": {
                    "enabled": True,
                    "hooks": {
                        "pre_validation": True,
                        "post_validation": True,
                        "on_error": True
                    },
                    "track_changes": True,
                    "collect_metrics": True
                },
                "gui_integration": {
                    "enabled": True,
                    "show_history_tab": True,
                    "real_time_updates": True,
                    "notification_level": "INFO"
                },
                "auto_start": {
                    "enabled": True,
                    "delay_seconds": 5,
                    "retry_attempts": 3
                }
            }
            
            integration_file = self.config_path / "history_integration.json"
            with open(integration_file, 'w', encoding='utf-8') as f:
                json.dump(integration_config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Configuração de integração criada: {integration_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar configurações: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """
        Inicializa o banco de dados do sistema histórico.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            db_path = self.history_data_path / "databases" / "history.db"
            
            # Criar o banco de dados usando DatabaseManager
            db_manager = DatabaseManager(str(db_path))
            
            if db_manager.initialize():
                self.logger.info(f"✅ Banco de dados inicializado: {db_path}")
                return True
            else:
                self.logger.error("❌ Falha ao inicializar banco de dados")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
            return False
    
    def setup_complete_system(self) -> bool:
        """
        Executa a configuração completa do sistema.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        self.logger.info("🚀 Iniciando configuração do Sistema de Visão Histórica...")
        
        steps = [
            ("Criando estrutura de diretórios", self.create_directory_structure),
            ("Criando configurações padrão", self.create_default_config),
            ("Inicializando banco de dados", self.initialize_database)
        ]
        
        for step_name, step_function in steps:
            self.logger.info(f"📋 {step_name}...")
            if not step_function():
                self.logger.error(f"❌ Falha em: {step_name}")
                return False
        
        self.logger.info("🎉 Sistema de Visão Histórica configurado com sucesso!")
        return True


def main():
    """
    Função principal do script de configuração.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Configuração do Sistema de Visão Histórica"
    )
    parser.add_argument(
        "--base-path",
        help="Caminho base do projeto",
        default=None
    )
    
    args = parser.parse_args()
    
    setup = HistorySystemSetup(args.base_path)
    
    if setup.setup_complete_system():
        print("✅ Configuração concluída com sucesso!")
        sys.exit(0)
    else:
        print("❌ Falha na configuração")
        sys.exit(1)


if __name__ == "__main__":
    main()