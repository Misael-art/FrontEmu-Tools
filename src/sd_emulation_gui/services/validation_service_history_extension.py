"""
Extensão do ValidationService para integração com o sistema histórico.
Adiciona hooks e funcionalidades de rastreamento sem modificar o código original.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps

# Adicionar o diretório history ao path para importar os módulos
history_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'history')
if history_path not in sys.path:
    sys.path.insert(0, history_path)

try:
    from history_manager import HistoryManager
    from change_tracker import ChangeTracker
    from metrics_collector import MetricsCollector
except ImportError as e:
    logging.warning(f"Não foi possível importar módulos do sistema histórico: {e}")
    HistoryManager = None
    ChangeTracker = None
    MetricsCollector = None


class ValidationServiceHistoryExtension:
    """
    Extensão para integrar o sistema histórico com o ValidationService.
    Fornece hooks e funcionalidades de rastreamento não-intrusivas.
    """
    
    def __init__(self, validation_service_instance):
        """
        Inicializa a extensão histórica.
        
        Args:
            validation_service_instance: Instância do ValidationService original
        """
        self.validation_service = validation_service_instance
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes do sistema histórico
        self.history_manager = None
        self.change_tracker = None
        self.metrics_collector = None
        
        self._initialize_history_components()
        self._setup_hooks()
    
    def _initialize_history_components(self):
        """
        Inicializa os componentes do sistema histórico.
        """
        try:
            if HistoryManager:
                self.history_manager = HistoryManager()
                self.logger.info("HistoryManager inicializado com sucesso")
            
            if ChangeTracker:
                self.change_tracker = ChangeTracker()
                self.logger.info("ChangeTracker inicializado com sucesso")
            
            if MetricsCollector:
                self.metrics_collector = MetricsCollector()
                self.logger.info("MetricsCollector inicializado com sucesso")
                
        except Exception as e:
            self.logger.error(f"Erro ao inicializar componentes históricos: {e}")
    
    def _setup_hooks(self):
        """
        Configura os hooks nos métodos do ValidationService.
        """
        if not hasattr(self.validation_service, '_original_validate_config'):
            # Salvar método original
            self.validation_service._original_validate_config = self.validation_service.validate_config
            # Substituir por versão com hooks
            self.validation_service.validate_config = self._validate_config_with_history
        
        if not hasattr(self.validation_service, '_original_validate_all'):
            # Salvar método original
            self.validation_service._original_validate_all = self.validation_service.validate_all
            # Substituir por versão com hooks
            self.validation_service.validate_all = self._validate_all_with_history
    
    def _validate_config_with_history(self, config_path: str) -> Dict[str, Any]:
        """
        Versão do validate_config com hooks históricos.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Resultado da validação
        """
        start_time = datetime.now()
        
        # Hook: antes da validação
        self._before_validation_hook(config_path, 'validate_config')
        
        try:
            # Executar validação original
            result = self.validation_service._original_validate_config(config_path)
            
            # Hook: após validação bem-sucedida
            self._after_validation_hook(config_path, 'validate_config', result, start_time)
            
            return result
            
        except Exception as e:
            # Hook: erro na validação
            self._validation_error_hook(config_path, 'validate_config', e, start_time)
            raise
    
    def _validate_all_with_history(self) -> Dict[str, Any]:
        """
        Versão do validate_all com hooks históricos.
        
        Returns:
            Resultado da validação completa
        """
        start_time = datetime.now()
        
        # Hook: antes da validação
        self._before_validation_hook('all_configs', 'validate_all')
        
        try:
            # Executar validação original
            result = self.validation_service._original_validate_all()
            
            # Hook: após validação bem-sucedida
            self._after_validation_hook('all_configs', 'validate_all', result, start_time)
            
            return result
            
        except Exception as e:
            # Hook: erro na validação
            self._validation_error_hook('all_configs', 'validate_all', e, start_time)
            raise
    
    def _before_validation_hook(self, target: str, operation: str):
        """
        Hook executado antes de uma validação.
        
        Args:
            target: Alvo da validação (arquivo ou 'all_configs')
            operation: Tipo de operação ('validate_config' ou 'validate_all')
        """
        try:
            if self.change_tracker:
                self.change_tracker.track_validation_start(target, operation)
            
            if self.metrics_collector:
                self.metrics_collector.record_validation_start(target, operation)
                
            self.logger.debug(f"Hook antes da validação: {operation} em {target}")
            
        except Exception as e:
            self.logger.error(f"Erro no hook antes da validação: {e}")
    
    def _after_validation_hook(self, target: str, operation: str, result: Dict[str, Any], start_time: datetime):
        """
        Hook executado após uma validação bem-sucedida.
        
        Args:
            target: Alvo da validação
            operation: Tipo de operação
            result: Resultado da validação
            start_time: Tempo de início da operação
        """
        try:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if self.change_tracker:
                self.change_tracker.track_validation_success(target, operation, result)
            
            if self.metrics_collector:
                self.metrics_collector.record_validation_success(target, operation, duration, result)
            
            if self.history_manager:
                self.history_manager.record_validation_event(target, operation, 'success', result)
                
            self.logger.debug(f"Hook após validação bem-sucedida: {operation} em {target} ({duration:.2f}s)")
            
        except Exception as e:
            self.logger.error(f"Erro no hook após validação: {e}")
    
    def _validation_error_hook(self, target: str, operation: str, error: Exception, start_time: datetime):
        """
        Hook executado quando ocorre erro na validação.
        
        Args:
            target: Alvo da validação
            operation: Tipo de operação
            error: Erro ocorrido
            start_time: Tempo de início da operação
        """
        try:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_info = {
                'type': type(error).__name__,
                'message': str(error),
                'duration': duration
            }
            
            if self.change_tracker:
                self.change_tracker.track_validation_error(target, operation, error_info)
            
            if self.metrics_collector:
                self.metrics_collector.record_validation_error(target, operation, duration, error_info)
            
            if self.history_manager:
                self.history_manager.record_validation_event(target, operation, 'error', error_info)
                
            self.logger.debug(f"Hook erro na validação: {operation} em {target} ({duration:.2f}s) - {error}")
            
        except Exception as e:
            self.logger.error(f"Erro no hook de erro de validação: {e}")
    
    def track_config_change(self, config_path: str, old_content: str, new_content: str):
        """
        Rastreia mudanças em arquivos de configuração.
        
        Args:
            config_path: Caminho do arquivo de configuração
            old_content: Conteúdo anterior
            new_content: Novo conteúdo
        """
        try:
            if self.change_tracker:
                self.change_tracker.track_config_change(config_path, old_content, new_content)
            
            if self.history_manager:
                self.history_manager.record_config_change(config_path, old_content, new_content)
                
            self.logger.info(f"Mudança rastreada em: {config_path}")
            
        except Exception as e:
            self.logger.error(f"Erro ao rastrear mudança de configuração: {e}")
    
    def get_validation_history(self, target: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém histórico de validações.
        
        Args:
            target: Alvo específico (opcional)
            limit: Limite de registros
            
        Returns:
            Lista de eventos de validação
        """
        try:
            if self.history_manager:
                return self.history_manager.get_validation_history(target, limit)
            return []
            
        except Exception as e:
            self.logger.error(f"Erro ao obter histórico de validações: {e}")
            return []
    
    def get_validation_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Obtém métricas de validação.
        
        Args:
            period_days: Período em dias
            
        Returns:
            Métricas de validação
        """
        try:
            if self.metrics_collector:
                return self.metrics_collector.get_validation_metrics(period_days)
            return {}
            
        except Exception as e:
            self.logger.error(f"Erro ao obter métricas de validação: {e}")
            return {}
    
    def generate_validation_report(self, output_path: str, period_days: int = 30):
        """
        Gera relatório de validação.
        
        Args:
            output_path: Caminho para salvar o relatório
            period_days: Período em dias
        """
        try:
            if self.history_manager:
                self.history_manager.generate_validation_report(output_path, period_days)
                self.logger.info(f"Relatório de validação gerado: {output_path}")
            else:
                self.logger.warning("HistoryManager não disponível para gerar relatório")
                
        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório de validação: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Remove dados antigos do sistema histórico.
        
        Args:
            days_to_keep: Dias de dados para manter
        """
        try:
            if self.history_manager:
                self.history_manager.cleanup_old_data(days_to_keep)
                self.logger.info(f"Limpeza de dados antigos concluída (mantidos {days_to_keep} dias)")
            
        except Exception as e:
            self.logger.error(f"Erro na limpeza de dados antigos: {e}")


def extend_validation_service(validation_service_instance):
    """
    Função utilitária para estender um ValidationService com funcionalidades históricas.
    
    Args:
        validation_service_instance: Instância do ValidationService
        
    Returns:
        Extensão histórica aplicada
    """
    extension = ValidationServiceHistoryExtension(validation_service_instance)
    
    # Adicionar métodos de conveniência ao ValidationService
    validation_service_instance.track_config_change = extension.track_config_change
    validation_service_instance.get_validation_history = extension.get_validation_history
    validation_service_instance.get_validation_metrics = extension.get_validation_metrics
    validation_service_instance.generate_validation_report = extension.generate_validation_report
    validation_service_instance.cleanup_old_data = extension.cleanup_old_data
    
    return extension


# Exemplo de uso:
# from validation_service import ValidationService
# from validation_service_history_extension import extend_validation_service
#
# validation_service = ValidationService()
# history_extension = extend_validation_service(validation_service)
#
# # Agora o ValidationService tem funcionalidades históricas
# result = validation_service.validate_config("config.json")
# history = validation_service.get_validation_history()
# metrics = validation_service.get_validation_metrics()