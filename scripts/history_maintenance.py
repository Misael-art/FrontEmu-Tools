#!/usr/bin/env python3
"""
Script de Manutenção do Sistema de Visão Histórica
Executa tarefas de manutenção automática do sistema histórico.

Autor: Sistema de Visão Histórica
Data: 2024
"""

import os
import sys
import json
import logging
import sqlite3
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from history.database_manager import DatabaseManager
    from history.backup_manager import BackupManager
    from history.config_manager import ConfigManager
    from history.history_manager import HistoryManager
except ImportError as e:
    print(f"⚠️ Erro ao importar módulos do sistema histórico: {e}")
    sys.exit(1)


class HistoryMaintenanceService:
    """
    Serviço de manutenção automática do sistema de visão histórica.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o serviço de manutenção.
        
        Args:
            config_path: Caminho para arquivo de configuração (opcional)
        """
        self.base_path = Path(__file__).parent.parent
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        self.logger = self._setup_logging()
        
        # Inicializar componentes
        self.db_manager = None
        self.backup_manager = None
        self._initialize_components()
        
    def _setup_logging(self) -> logging.Logger:
        """
        Configura o sistema de logging.
        
        Returns:
            Logger configurado
        """
        logger = logging.getLogger('history_maintenance')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Handler para console
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # Handler para arquivo (se configurado)
            log_file = self.config.get('logging', {}).get('file')
            if log_file:
                log_path = self.base_path / log_file
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(log_path)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        
        return logger
    
    def _initialize_components(self):
        """
        Inicializa os componentes necessários para manutenção.
        """
        try:
            db_path = self.base_path / self.config.get('database', {}).get('path', 'history_data/databases/history.db')
            self.db_manager = DatabaseManager(str(db_path))
            
            backup_config = self.config.get('database', {})
            self.backup_manager = BackupManager(
                db_path=str(db_path),
                backup_dir=str(self.base_path / "history_data" / "backups"),
                max_backups=backup_config.get('max_backup_files', 10)
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar componentes: {e}")
    
    def cleanup_old_records(self, retention_days: int = 30) -> Tuple[bool, Dict]:
        """
        Remove registros antigos do banco de dados.
        
        Args:
            retention_days: Dias de retenção dos dados
            
        Returns:
            Tupla (sucesso, estatísticas)
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            stats = {
                'changes_deleted': 0,
                'metrics_deleted': 0,
                'sessions_deleted': 0,
                'cutoff_date': cutoff_date.isoformat()
            }
            
            if not self.db_manager:
                return False, stats
            
            # Limpar tabela de mudanças
            changes_query = "DELETE FROM changes WHERE timestamp < ?"
            changes_result = self.db_manager.execute_query(changes_query, (cutoff_date,))
            if changes_result:
                stats['changes_deleted'] = changes_result.get('rows_affected', 0)
            
            # Limpar tabela de métricas
            metrics_query = "DELETE FROM metrics WHERE timestamp < ?"
            metrics_result = self.db_manager.execute_query(metrics_query, (cutoff_date,))
            if metrics_result:
                stats['metrics_deleted'] = metrics_result.get('rows_affected', 0)
            
            # Limpar sessões antigas
            sessions_query = "DELETE FROM operation_sessions WHERE start_time < ?"
            sessions_result = self.db_manager.execute_query(sessions_query, (cutoff_date,))
            if sessions_result:
                stats['sessions_deleted'] = sessions_result.get('rows_affected', 0)
            
            # Executar VACUUM para otimizar o banco
            self.db_manager.execute_query("VACUUM")
            
            total_deleted = stats['changes_deleted'] + stats['metrics_deleted'] + stats['sessions_deleted']
            self.logger.info(f"✅ Limpeza concluída: {total_deleted} registros removidos")
            
            return True, stats
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante limpeza: {e}")
            return False, stats
    
    def optimize_database(self) -> Tuple[bool, Dict]:
        """
        Otimiza o banco de dados.
        
        Returns:
            Tupla (sucesso, estatísticas)
        """
        try:
            stats = {
                'size_before': 0,
                'size_after': 0,
                'indexes_rebuilt': 0
            }
            
            if not self.db_manager:
                return False, stats
            
            db_path = Path(self.db_manager.db_path)
            if db_path.exists():
                stats['size_before'] = db_path.stat().st_size
            
            # Recriar índices
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON changes(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_changes_type ON changes(change_type)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_start ON operation_sessions(start_time)"
            ]
            
            for index_sql in indexes:
                try:
                    self.db_manager.execute_query(index_sql)
                    stats['indexes_rebuilt'] += 1
                except Exception as e:
                    self.logger.warning(f"Erro ao criar índice: {e}")
            
            # Analisar estatísticas
            self.db_manager.execute_query("ANALYZE")
            
            # Verificar tamanho após otimização
            if db_path.exists():
                stats['size_after'] = db_path.stat().st_size
            
            size_reduction = stats['size_before'] - stats['size_after']
            self.logger.info(f"✅ Otimização concluída: {size_reduction} bytes economizados")
            
            return True, stats
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante otimização: {e}")
            return False, stats
    
    def create_backup(self) -> Tuple[bool, str]:
        """
        Cria backup do banco de dados.
        
        Returns:
            Tupla (sucesso, caminho do backup)
        """
        try:
            if not self.backup_manager:
                return False, ""
            
            backup_path = self.backup_manager.create_backup()
            if backup_path:
                self.logger.info(f"✅ Backup criado: {backup_path}")
                return True, backup_path
            else:
                self.logger.error("❌ Falha ao criar backup")
                return False, ""
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar backup: {e}")
            return False, ""
    
    def cleanup_old_backups(self) -> Tuple[bool, int]:
        """
        Remove backups antigos.
        
        Returns:
            Tupla (sucesso, número de backups removidos)
        """
        try:
            if not self.backup_manager:
                return False, 0
            
            removed_count = self.backup_manager.cleanup_old_backups()
            self.logger.info(f"✅ {removed_count} backups antigos removidos")
            
            return True, removed_count
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar backups: {e}")
            return False, 0
    
    def cleanup_old_reports(self, retention_days: int = 90) -> Tuple[bool, int]:
        """
        Remove relatórios antigos.
        
        Args:
            retention_days: Dias de retenção dos relatórios
            
        Returns:
            Tupla (sucesso, número de relatórios removidos)
        """
        try:
            reports_dir = self.base_path / "history_data" / "reports"
            if not reports_dir.exists():
                return True, 0
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            removed_count = 0
            
            for report_file in reports_dir.glob("*.html"):
                try:
                    file_time = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        report_file.unlink()
                        removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Erro ao remover relatório {report_file}: {e}")
            
            self.logger.info(f"✅ {removed_count} relatórios antigos removidos")
            return True, removed_count
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar relatórios: {e}")
            return False, 0
    
    def cleanup_old_logs(self, retention_days: int = 30) -> Tuple[bool, int]:
        """
        Remove logs antigos.
        
        Args:
            retention_days: Dias de retenção dos logs
            
        Returns:
            Tupla (sucesso, número de logs removidos)
        """
        try:
            logs_dir = self.base_path / "history_data" / "logs"
            if not logs_dir.exists():
                return True, 0
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            removed_count = 0
            
            for log_file in logs_dir.glob("*.log*"):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        log_file.unlink()
                        removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Erro ao remover log {log_file}: {e}")
            
            self.logger.info(f"✅ {removed_count} logs antigos removidos")
            return True, removed_count
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar logs: {e}")
            return False, 0
    
    def get_system_health(self) -> Dict:
        """
        Obtém informações sobre a saúde do sistema.
        
        Returns:
            Dicionário com informações de saúde
        """
        health = {
            'timestamp': datetime.now().isoformat(),
            'database': {'status': 'unknown', 'size': 0, 'tables': 0},
            'backups': {'count': 0, 'latest': None},
            'reports': {'count': 0, 'latest': None},
            'logs': {'count': 0, 'size': 0}
        }
        
        try:
            # Status do banco de dados
            if self.db_manager:
                db_path = Path(self.db_manager.db_path)
                if db_path.exists():
                    health['database']['status'] = 'ok'
                    health['database']['size'] = db_path.stat().st_size
                    
                    # Contar tabelas
                    try:
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                        health['database']['tables'] = cursor.fetchone()[0]
                        conn.close()
                    except Exception:
                        pass
                else:
                    health['database']['status'] = 'missing'
            
            # Status dos backups
            backups_dir = self.base_path / "history_data" / "backups"
            if backups_dir.exists():
                backup_files = list(backups_dir.glob("*.db"))
                health['backups']['count'] = len(backup_files)
                if backup_files:
                    latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                    health['backups']['latest'] = latest_backup.name
            
            # Status dos relatórios
            reports_dir = self.base_path / "history_data" / "reports"
            if reports_dir.exists():
                report_files = list(reports_dir.glob("*.html"))
                health['reports']['count'] = len(report_files)
                if report_files:
                    latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
                    health['reports']['latest'] = latest_report.name
            
            # Status dos logs
            logs_dir = self.base_path / "history_data" / "logs"
            if logs_dir.exists():
                log_files = list(logs_dir.glob("*.log*"))
                health['logs']['count'] = len(log_files)
                health['logs']['size'] = sum(f.stat().st_size for f in log_files)
            
        except Exception as e:
            self.logger.error(f"Erro ao obter saúde do sistema: {e}")
        
        return health
    
    def run_full_maintenance(self) -> Dict:
        """
        Executa manutenção completa do sistema.
        
        Returns:
            Relatório da manutenção
        """
        self.logger.info("🔧 Iniciando manutenção completa do Sistema de Visão Histórica...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'tasks': {},
            'health_before': self.get_system_health(),
            'health_after': {},
            'success': True
        }
        
        # Lista de tarefas de manutenção
        maintenance_tasks = [
            ('backup', 'Criando backup', self.create_backup),
            ('cleanup_records', 'Limpando registros antigos', lambda: self.cleanup_old_records(30)),
            ('optimize_db', 'Otimizando banco de dados', self.optimize_database),
            ('cleanup_backups', 'Limpando backups antigos', self.cleanup_old_backups),
            ('cleanup_reports', 'Limpando relatórios antigos', lambda: self.cleanup_old_reports(90)),
            ('cleanup_logs', 'Limpando logs antigos', lambda: self.cleanup_old_logs(30))
        ]
        
        # Executar tarefas
        for task_id, task_name, task_function in maintenance_tasks:
            self.logger.info(f"📋 {task_name}...")
            try:
                result = task_function()
                report['tasks'][task_id] = {
                    'name': task_name,
                    'success': True,
                    'result': result
                }
            except Exception as e:
                self.logger.error(f"❌ Erro em {task_name}: {e}")
                report['tasks'][task_id] = {
                    'name': task_name,
                    'success': False,
                    'error': str(e)
                }
                report['success'] = False
        
        # Saúde após manutenção
        report['health_after'] = self.get_system_health()
        
        if report['success']:
            self.logger.info("✅ Manutenção completa concluída com sucesso!")
        else:
            self.logger.warning("⚠️ Manutenção concluída com alguns erros")
        
        return report


def main():
    """
    Função principal do script de manutenção.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manutenção do Sistema de Visão Histórica"
    )
    parser.add_argument(
        "--config",
        help="Caminho para arquivo de configuração",
        default=None
    )
    parser.add_argument(
        "--task",
        choices=['full', 'backup', 'cleanup', 'optimize', 'health'],
        default='full',
        help="Tarefa específica a executar"
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Dias de retenção para limpeza"
    )
    parser.add_argument(
        "--output",
        help="Arquivo para salvar relatório (JSON)",
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        maintenance = HistoryMaintenanceService(args.config)
        
        if args.task == 'health':
            health = maintenance.get_system_health()
            print(json.dumps(health, indent=2, ensure_ascii=False))
            
        elif args.task == 'backup':
            success, backup_path = maintenance.create_backup()
            if success:
                print(f"✅ Backup criado: {backup_path}")
            else:
                print("❌ Falha ao criar backup")
                sys.exit(1)
                
        elif args.task == 'cleanup':
            success, stats = maintenance.cleanup_old_records(args.retention_days)
            if success:
                print(f"✅ Limpeza concluída: {json.dumps(stats, indent=2)}")
            else:
                print("❌ Falha na limpeza")
                sys.exit(1)
                
        elif args.task == 'optimize':
            success, stats = maintenance.optimize_database()
            if success:
                print(f"✅ Otimização concluída: {json.dumps(stats, indent=2)}")
            else:
                print("❌ Falha na otimização")
                sys.exit(1)
                
        else:  # full
            report = maintenance.run_full_maintenance()
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"📄 Relatório salvo em: {args.output}")
            else:
                print(json.dumps(report, indent=2, ensure_ascii=False))
            
            if not report['success']:
                sys.exit(1)
    
    except Exception as e:
        print(f"❌ Erro durante manutenção: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main(