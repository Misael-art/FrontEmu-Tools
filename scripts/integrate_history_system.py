#!/usr/bin/env python3
"""
Script de Integração do Sistema de Visão Histórica
Integra o sistema histórico com o ValidationService do SD Emulation GUI.

Autor: Sistema de Visão Histórica
Data: 2024
"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from history.history_manager import HistoryManager
    from history.config_manager import ConfigManager
except ImportError as e:
    print(f"⚠️ Erro ao importar módulos do sistema histórico: {e}")
    sys.exit(1)


class HistorySystemIntegrator:
    """
    Classe responsável pela integração do sistema histórico com o ValidationService.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa o integrador do sistema histórico.
        
        Args:
            base_path: Caminho base do projeto (opcional)
        """
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.src_path = self.base_path / "src"
        self.validation_service_path = self.src_path / "validation_service.py"
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """
        Configura o sistema de logging.
        
        Returns:
            Logger configurado
        """
        logger = logging.getLogger('history_integrator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def backup_validation_service(self) -> bool:
        """
        Cria backup do ValidationService antes da modificação.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            if not self.validation_service_path.exists():
                self.logger.error(f"❌ ValidationService não encontrado: {self.validation_service_path}")
                return False
            
            backup_path = self.validation_service_path.with_suffix('.py.backup')
            shutil.copy2(self.validation_service_path, backup_path)
            
            self.logger.info(f"✅ Backup criado: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar backup: {e}")
            return False
    
    def read_validation_service(self) -> Optional[str]:
        """
        Lê o conteúdo atual do ValidationService.
        
        Returns:
            Conteúdo do arquivo ou None se erro
        """
        try:
            with open(self.validation_service_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"❌ Erro ao ler ValidationService: {e}")
            return None
    
    def write_validation_service(self, content: str) -> bool:
        """
        Escreve o conteúdo modificado no ValidationService.
        
        Args:
            content: Novo conteúdo do arquivo
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            with open(self.validation_service_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info("✅ ValidationService atualizado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao escrever ValidationService: {e}")
            return False
    
    def add_history_imports(self, content: str) -> str:
        """
        Adiciona imports do sistema histórico ao ValidationService.
        
        Args:
            content: Conteúdo atual do arquivo
            
        Returns:
            Conteúdo modificado
        """
        # Procurar por imports existentes
        lines = content.split('\n')
        import_end_index = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_end_index = i
        
        # Adicionar imports do sistema histórico
        history_imports = [
            "",
            "# Imports do Sistema de Visão Histórica",
            "try:",
            "    from history.history_manager import HistoryManager",
            "    from history.config_manager import ConfigManager",
            "    HISTORY_AVAILABLE = True",
            "except ImportError:",
            "    HISTORY_AVAILABLE = False",
            "    print('⚠️ Sistema de Visão Histórica não disponível')",
            ""
        ]
        
        # Inserir após os imports existentes
        lines[import_end_index + 1:import_end_index + 1] = history_imports
        
        return '\n'.join(lines)
    
    def add_history_initialization(self, content: str) -> str:
        """
        Adiciona inicialização do sistema histórico ao ValidationService.
        
        Args:
            content: Conteúdo atual do arquivo
            
        Returns:
            Conteúdo modificado
        """
        # Procurar pela classe ValidationService
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'class ValidationService' in line:
                # Procurar pelo método __init__
                for j in range(i, len(lines)):
                    if 'def __init__' in lines[j]:
                        # Encontrar o final do método __init__
                        indent_level = len(lines[j]) - len(lines[j].lstrip())
                        
                        for k in range(j + 1, len(lines)):
                            current_line = lines[k]
                            if current_line.strip() == '':
                                continue
                            
                            current_indent = len(current_line) - len(current_line.lstrip())
                            
                            # Se encontrou uma linha com indentação menor ou igual, inserir antes
                            if current_indent <= indent_level and current_line.strip():
                                history_init = [
                                    "",
                                    "        # Inicializar Sistema de Visão Histórica",
                                    "        self.history_manager = None",
                                    "        if HISTORY_AVAILABLE:",
                                    "            try:",
                                    "                self.history_manager = HistoryManager()",
                                    "                self.history_manager.start()",
                                    "                print('✅ Sistema de Visão Histórica iniciado')",
                                    "            except Exception as e:",
                                    "                print(f'⚠️ Erro ao iniciar Sistema de Visão Histórica: {e}')",
                                    ""
                                ]
                                
                                lines[k:k] = history_init
                                return '\n'.join(lines)
                        break
                break
        
        return content
    
    def add_history_hooks(self, content: str) -> str:
        """
        Adiciona hooks do sistema histórico aos métodos de validação.
        
        Args:
            content: Conteúdo atual do arquivo
            
        Returns:
            Conteúdo modificado
        """
        lines = content.split('\n')
        
        # Procurar por métodos de validação para adicionar hooks
        validation_methods = ['validate_file', 'validate_directory', 'validate_config']
        
        for method_name in validation_methods:
            for i, line in enumerate(lines):
                if f'def {method_name}' in line:
                    # Adicionar hook no início do método
                    indent = '        '  # Assumindo indentação padrão
                    
                    pre_hook = [
                        f"{indent}# Hook pré-validação do Sistema Histórico",
                        f"{indent}if self.history_manager:",
                        f"{indent}    try:",
                        f"{indent}        self.history_manager.log_change(",
                        f"{indent}            change_type='validation_start',",
                        f"{indent}            description=f'Iniciando {method_name}',",
                        f"{indent}            metadata={{'method': '{method_name}', 'args': str(locals())}}",
                        f"{indent}        )",
                        f"{indent}    except Exception as e:",
                        f"{indent}        print(f'⚠️ Erro no hook pré-validação: {{e}}')",
                        ""
                    ]
                    
                    # Inserir após a linha de definição do método
                    lines[i + 1:i + 1] = pre_hook
                    
                    # Procurar pelo return do método para adicionar hook pós-validação
                    for j in range(i + len(pre_hook) + 1, len(lines)):
                        if 'return ' in lines[j] and lines[j].strip().startswith('return'):
                            post_hook = [
                                "",
                                f"{indent}# Hook pós-validação do Sistema Histórico",
                                f"{indent}if self.history_manager:",
                                f"{indent}    try:",
                                f"{indent}        self.history_manager.log_change(",
                                f"{indent}            change_type='validation_end',",
                                f"{indent}            description=f'Finalizando {method_name}',",
                                f"{indent}            metadata={{'method': '{method_name}', 'result': 'success'}}",
                                f"{indent}        )",
                                f"{indent}    except Exception as e:",
                                f"{indent}        print(f'⚠️ Erro no hook pós-validação: {{e}}')",
                                ""
                            ]
                            
                            lines[j:j] = post_hook
                            break
                    break
        
        return '\n'.join(lines)
    
    def integrate_with_validation_service(self) -> bool:
        """
        Executa a integração completa com o ValidationService.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            self.logger.info("🔗 Iniciando integração com ValidationService...")
            
            # Criar backup
            if not self.backup_validation_service():
                return False
            
            # Ler conteúdo atual
            content = self.read_validation_service()
            if content is None:
                return False
            
            # Verificar se já está integrado
            if 'HistoryManager' in content:
                self.logger.info("ℹ️ ValidationService já possui integração com Sistema Histórico")
                return True
            
            # Aplicar modificações
            self.logger.info("📝 Adicionando imports do sistema histórico...")
            content = self.add_history_imports(content)
            
            self.logger.info("🔧 Adicionando inicialização do sistema histórico...")
            content = self.add_history_initialization(content)
            
            self.logger.info("🪝 Adicionando hooks de validação...")
            content = self.add_history_hooks(content)
            
            # Salvar arquivo modificado
            if not self.write_validation_service(content):
                return False
            
            self.logger.info("✅ Integração com ValidationService concluída!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante integração: {e}")
            return False
    
    def verify_integration(self) -> bool:
        """
        Verifica se a integração foi bem-sucedida.
        
        Returns:
            True se integração está funcionando, False caso contrário
        """
        try:
            content = self.read_validation_service()
            if content is None:
                return False
            
            # Verificar se os componentes necessários estão presentes
            required_components = [
                'HistoryManager',
                'HISTORY_AVAILABLE',
                'self.history_manager',
                'validation_start',
                'validation_end'
            ]
            
            for component in required_components:
                if component not in content:
                    self.logger.error(f"❌ Componente não encontrado: {component}")
                    return False
            
            self.logger.info("✅ Verificação da integração bem-sucedida")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante verificação: {e}")
            return False
    
    def rollback_integration(self) -> bool:
        """
        Desfaz a integração restaurando o backup.
        
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            backup_path = self.validation_service_path.with_suffix('.py.backup')
            
            if not backup_path.exists():
                self.logger.error("❌ Arquivo de backup não encontrado")
                return False
            
            shutil.copy2(backup_path, self.validation_service_path)
            self.logger.info("✅ Integração desfeita, backup restaurado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao desfazer integração: {e}")
            return False


def main():
    """
    Função principal do script de integração.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integração do Sistema de Visão Histórica com ValidationService"
    )
    parser.add_argument(
        "--base-path",
        help="Caminho base do projeto",
        default=None
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Apenas verificar a integração existente"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Desfazer a integração"
    )
    
    args = parser.parse_args()
    
    integrator = HistorySystemIntegrator(args.base_path)
    
    if args.rollback:
        if integrator.rollback_integration():
            print("✅ Integração desfeita com sucesso!")
            sys.exit(0)
        else:
            print("❌ Falha ao desfazer integração")
            sys.exit(1)
    elif args.verify_only:
        if integrator.verify_integration():
            print("✅ Integração está funcionando corretamente")
            sys.exit(0)
        else:
            print("❌ Problemas encontrados na integração")
            sys.exit(1)
    else:
        if integrator.integrate_with_validation_service():
            if integrator.verify_integration():
                print("✅ Integração concluída e verificada com sucesso!")
                sys.exit(0)
            else:
                print("⚠️ Integração concluída mas verificação falhou")
                sys.exit(1)
        else:
            print("❌ Falha na integração")
            sys.exit(1)


if __name__ == "__main__