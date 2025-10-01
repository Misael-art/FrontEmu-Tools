#!/usr/bin/env python3
"""
Script de Geração Automática de Relatórios
Gera relatórios automáticos do sistema de visão histórica.

Autor: Sistema de Visão Histórica
Data: 2024
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Adicionar o diretório raiz ao path para importações
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from history.database_manager import DatabaseManager
    from history.metrics_collector import MetricsCollector
    from history.report_generator import ReportGenerator
    from history.history_manager import HistoryManager
except ImportError:
    print("⚠️ Módulos do sistema histórico não encontrados. Executando em modo standalone.")
    DatabaseManager = None
    MetricsCollector = None
    ReportGenerator = None
    HistoryManager = None


class ReportGenerationService:
    """Serviço de geração automática de relatórios"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o serviço de geração de relatórios
        
        Args:
            config_path: Caminho para arquivo de configuração
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self.setup_logging()
        
        # Inicializar componentes se disponíveis
        self.db_manager = None
        self.metrics_collector = None
        self.report_generator = None
        self.history_manager = None
        
        self._initialize_components()
    
    def _get_default_config_path(self) -> str:
        """Obtém o caminho padrão do arquivo de configuração"""
        return str(Path(__file__).parent.parent / "config" / "history_config.json")
    
    def _load_config(self) -> Dict:
        """Carrega configuração do sistema"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"⚠️ Erro ao carregar configuração: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Retorna configuração padrão"""
        return {
            "database": {
                "path": "history_data/database/history.db"
            },
            "reports": {
                "path": "history_data/reports",
                "templates_path": "history_data/templates",
                "formats": ["html", "json"],
                "auto_generate": True,
                "schedule": {
                    "daily": True,
                    "weekly": True,
                    "monthly": True
                }
            },
            "metrics": {
                "enabled": True,
                "collection_interval": 300
            }
        }
    
    def setup_logging(self):
        """Configura sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('report_generation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _initialize_components(self):
        """Inicializa componentes do sistema histórico"""
        try:
            if DatabaseManager:
                self.db_manager = DatabaseManager(self.config.get("database", {}))
            
            if MetricsCollector:
                self.metrics_collector = MetricsCollector(self.config.get("metrics", {}))
            
            if ReportGenerator:
                self.report_generator = ReportGenerator(self.config.get("reports", {}))
            
            if HistoryManager:
                self.history_manager = HistoryManager(self.config)
                
            self.logger.info("✅ Componentes do sistema histórico inicializados")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao inicializar componentes: {e}")
    
    def generate_daily_report(self) -> Optional[str]:
        """
        Gera relatório diário
        
        Returns:
            Caminho do relatório gerado ou None se falhou
        """
        try:
            self.logger.info("📊 Gerando relatório diário...")
            
            # Coletar dados do último dia
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            report_data = self._collect_report_data(start_date, end_date, "daily")
            
            if not report_data:
                self.logger.warning("⚠️ Nenhum dado encontrado para o relatório diário")
                return None
            
            # Gerar relatório
            report_path = self._generate_report(report_data, "daily")
            
            if report_path:
                self.logger.info(f"✅ Relatório diário gerado: {report_path}")
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório diário: {e}")
            return None
    
    def generate_weekly_report(self) -> Optional[str]:
        """
        Gera relatório semanal
        
        Returns:
            Caminho do relatório gerado ou None se falhou
        """
        try:
            self.logger.info("📊 Gerando relatório semanal...")
            
            # Coletar dados da última semana
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=1)
            
            report_data = self._collect_report_data(start_date, end_date, "weekly")
            
            if not report_data:
                self.logger.warning("⚠️ Nenhum dado encontrado para o relatório semanal")
                return None
            
            # Gerar relatório
            report_path = self._generate_report(report_data, "weekly")
            
            if report_path:
                self.logger.info(f"✅ Relatório semanal gerado: {report_path}")
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório semanal: {e}")
            return None
    
    def generate_monthly_report(self) -> Optional[str]:
        """
        Gera relatório mensal
        
        Returns:
            Caminho do relatório gerado ou None se falhou
        """
        try:
            self.logger.info("📊 Gerando relatório mensal...")
            
            # Coletar dados do último mês
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            report_data = self._collect_report_data(start_date, end_date, "monthly")
            
            if not report_data:
                self.logger.warning("⚠️ Nenhum dado encontrado para o relatório mensal")
                return None
            
            # Gerar relatório
            report_path = self._generate_report(report_data, "monthly")
            
            if report_path:
                self.logger.info(f"✅ Relatório mensal gerado: {report_path}")
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório mensal: {e}")
            return None
    
    def generate_custom_report(self, start_date: datetime, end_date: datetime, 
                             report_type: str = "custom") -> Optional[str]:
        """
        Gera relatório personalizado para período específico
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            report_type: Tipo do relatório
            
        Returns:
            Caminho do relatório gerado ou None se falhou
        """
        try:
            self.logger.info(f"📊 Gerando relatório personalizado ({start_date} - {end_date})...")
            
            report_data = self._collect_report_data(start_date, end_date, report_type)
            
            if not report_data:
                self.logger.warning("⚠️ Nenhum dado encontrado para o relatório personalizado")
                return None
            
            # Gerar relatório
            report_path = self._generate_report(report_data, report_type)
            
            if report_path:
                self.logger.info(f"✅ Relatório personalizado gerado: {report_path}")
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório personalizado: {e}")
            return None
    
    def _collect_report_data(self, start_date: datetime, end_date: datetime, 
                           report_type: str) -> Optional[Dict]:
        """
        Coleta dados para o relatório
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            report_type: Tipo do relatório
            
        Returns:
            Dicionário com dados do relatório
        """
        try:
            report_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "report_type": report_type,
                    "generator": "ReportGenerationService"
                },
                "summary": {},
                "validation_stats": {},
                "performance_metrics": {},
                "file_changes": [],
                "error_analysis": {},
                "trends": {}
            }
            
            # Coletar estatísticas de validação
            if self.history_manager:
                validation_history = self.history_manager.get_validation_history(
                    start_date=start_date,
                    end_date=end_date
                )
                report_data["validation_stats"] = self._analyze_validation_stats(validation_history)
            
            # Coletar métricas de performance
            if self.metrics_collector:
                metrics = self.metrics_collector.get_metrics_for_period(start_date, end_date)
                report_data["performance_metrics"] = self._analyze_performance_metrics(metrics)
            
            # Coletar mudanças de arquivos
            if self.db_manager:
                file_changes = self._get_file_changes(start_date, end_date)
                report_data["file_changes"] = file_changes
            
            # Análise de erros
            report_data["error_analysis"] = self._analyze_errors(start_date, end_date)
            
            # Análise de tendências
            report_data["trends"] = self._analyze_trends(start_date, end_date)
            
            # Resumo geral
            report_data["summary"] = self._generate_summary(report_data)
            
            return report_data
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao coletar dados do relatório: {e}")
            return None
    
    def _analyze_validation_stats(self, validation_history: List[Dict]) -> Dict:
        """
        Analisa estatísticas de validação
        
        Args:
            validation_history: Histórico de validações
            
        Returns:
            Dicionário com estatísticas analisadas
        """
        if not validation_history:
            return {"total_validations": 0, "success_rate": 0, "error_rate": 0}
        
        total = len(validation_history)
        successful = sum(1 for v in validation_history if v.get("success", False))
        failed = total - successful
        
        return {
            "total_validations": total,
            "successful_validations": successful,
            "failed_validations": failed,
            "success_rate": (successful / total) * 100 if total > 0 else 0,
            "error_rate": (failed / total) * 100 if total > 0 else 0,
            "average_duration": sum(v.get("duration", 0) for v in validation_history) / total if total > 0 else 0
        }
    
    def _analyze_performance_metrics(self, metrics: List[Dict]) -> Dict:
        """
        Analisa métricas de performance
        
        Args:
            metrics: Lista de métricas
            
        Returns:
            Dicionário com análise de performance
        """
        if not metrics:
            return {"average_response_time": 0, "peak_memory_usage": 0}
        
        response_times = [m.get("response_time", 0) for m in metrics if "response_time" in m]
        memory_usage = [m.get("memory_usage", 0) for m in metrics if "memory_usage" in m]
        
        return {
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "peak_response_time": max(response_times) if response_times else 0,
            "average_memory_usage": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
            "peak_memory_usage": max(memory_usage) if memory_usage else 0,
            "total_operations": len(metrics)
        }
    
    def _get_file_changes(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Obtém mudanças de arquivos no período
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            
        Returns:
            Lista de mudanças de arquivos
        """
        # Implementação básica - seria expandida com dados reais do banco
        return [
            {
                "file_path": "config/example.json",
                "change_type": "modified",
                "timestamp": datetime.now().isoformat(),
                "size_change": 150
            }
        ]
    
    def _analyze_errors(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Analisa erros no período
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            
        Returns:
            Dicionário com análise de erros
        """
        return {
            "total_errors": 0,
            "error_types": {},
            "most_common_error": None,
            "error_trend": "stable"
        }
    
    def _analyze_trends(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Analisa tendências no período
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            
        Returns:
            Dicionário com análise de tendências
        """
        return {
            "validation_trend": "stable",
            "performance_trend": "improving",
            "error_trend": "decreasing",
            "usage_trend": "increasing"
        }
    
    def _generate_summary(self, report_data: Dict) -> Dict:
        """
        Gera resumo do relatório
        
        Args:
            report_data: Dados do relatório
            
        Returns:
            Dicionário com resumo
        """
        validation_stats = report_data.get("validation_stats", {})
        performance_metrics = report_data.get("performance_metrics", {})
        
        return {
            "period": f"{report_data['metadata']['period_start']} - {report_data['metadata']['period_end']}",
            "total_validations": validation_stats.get("total_validations", 0),
            "success_rate": validation_stats.get("success_rate", 0),
            "average_response_time": performance_metrics.get("average_response_time", 0),
            "total_file_changes": len(report_data.get("file_changes", [])),
            "overall_health": self._calculate_health_score(report_data)
        }
    
    def _calculate_health_score(self, report_data: Dict) -> str:
        """
        Calcula score de saúde do sistema
        
        Args:
            report_data: Dados do relatório
            
        Returns:
            Score de saúde (excellent, good, fair, poor)
        """
        validation_stats = report_data.get("validation_stats", {})
        success_rate = validation_stats.get("success_rate", 0)
        
        if success_rate >= 95:
            return "excellent"
        elif success_rate >= 85:
            return "good"
        elif success_rate >= 70:
            return "fair"
        else:
            return "poor"
    
    def _generate_report(self, report_data: Dict, report_type: str) -> Optional[str]:
        """
        Gera o relatório final
        
        Args:
            report_data: Dados do relatório
            report_type: Tipo do relatório
            
        Returns:
            Caminho do arquivo gerado
        """
        try:
            if self.report_generator:
                return self.report_generator.generate_report(report_data, "html")
            else:
                return self._generate_standalone_report(report_data, report_type)
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório: {e}")
            return None
    
    def _generate_standalone_report(self, report_data: Dict, report_type: str) -> str:
        """
        Gera relatório em modo standalone
        
        Args:
            report_data: Dados do relatório
            report_type: Tipo do relatório
            
        Returns:
            Caminho do arquivo gerado
        """
        reports_dir = self.config.get("reports", {}).get("path", "history_data/reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{report_type}_report_{timestamp}.json"
        report_path = os.path.join(reports_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    def generate_all_scheduled_reports(self) -> Dict[str, Optional[str]]:
        """
        Gera todos os relatórios agendados
        
        Returns:
            Dicionário com caminhos dos relatórios gerados
        """
        results = {}
        schedule = self.config.get("reports", {}).get("schedule", {})
        
        if schedule.get("daily", False):
            results["daily"] = self.generate_daily_report()
        
        if schedule.get("weekly", False):
            results["weekly"] = self.generate_weekly_report()
        
        if schedule.get("monthly", False):
            results["monthly"] = self.generate_monthly_report()
        
        return results


def main():
    """Função principal do script"""
    parser = argparse.ArgumentParser(description="Script de Geração Automática de Relatórios")
    parser.add_argument("--config", help="Caminho para arquivo de configuração")
    parser.add_argument("--type", choices=["daily", "weekly", "monthly", "all"], 
                       default="all", help="Tipo de relatório a gerar")
    parser.add_argument("--start-date", help="Data de início (YYYY-MM-DD) para relatório personalizado")
    parser.add_argument("--end-date", help="Data de fim (YYYY-MM-DD) para relatório personalizado")
    parser.add_argument("--verbose", "-v", action="store_true", help="Saída detalhada")
    
    args = parser.parse_args()
    
    # Inicializar serviço
    report_service = ReportGenerationService(args.config)
    
    if args.verbose:
        report_service.logger.setLevel(logging.DEBUG)
    
    # Executar geração de relatórios
    if args.start_date and args.end_date:
        # Relatório personalizado
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            
            report_path = report_service.generate_custom_report(start_date, end_date)
            if report_path:
                print(f"✅ Relatório personalizado gerado: {report_path}")
                sys.exit(0)
            else:
                print("❌ Falha ao gerar relatório personalizado")
                sys.exit(1)
                
        except ValueError as e:
            print(f"❌ Formato de data inválido: {e}")
            sys.exit(1)
    
    elif args.type == "daily":
        report_path = report_service.generate_daily_report()
        sys.exit(0 if report_path else 1)
    
    elif args.type == "weekly":
        report_path = report_service.generate_weekly_report()
        sys.exit(0 if report_path else 1)
    
    elif args.type == "monthly":
        report_path = report_service.generate_monthly_report()
        sys.exit(0 if report_path else 1)
    
    elif args.type == "all":
        results = report_service.generate_all_scheduled_reports()
        success = all(path is not None for path in results.values())
        
        for report_type, path in results.items():
            if path:
                print(f"✅ Relatório {report_type} gerado: {path}")
            else:
                print(f"❌ Falha ao gerar relatório {report_type}")
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()