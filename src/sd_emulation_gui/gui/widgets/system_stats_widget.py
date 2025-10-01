"""
System Stats Widget

Widget para visualização de estatísticas do sistema em tempo real,
incluindo métricas de performance, uso de recursos e alertas.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

try:
    from PySide6.QtCore import QTimer, Signal, QThread, Qt, QModelIndex
    from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QGroupBox, QProgressBar, QGridLayout, QFrame, QScrollArea,
        QMessageBox, QSizePolicy, QSpacerItem, QComboBox, QTableView,
        QHeaderView, QCheckBox, QSpinBox, QLineEdit, QTextEdit,
        QTabWidget, QListWidget, QListWidgetItem, QAbstractItemView,
        QSlider, QSplitter
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes for non-GUI environments
    class QWidget:
        def __init__(self, parent=None): pass
    class Signal: pass
    class QThread: pass


class SystemStatsWorker(QThread):
    """Worker thread para coleta de estatísticas do sistema."""
    
    # Signals
    stats_updated = Signal(dict)
    alert_triggered = Signal(str, str)
    error_occurred = Signal(str)
    
    def __init__(self, container, update_interval=5):
        """Inicializa o worker de estatísticas.
        
        Args:
            container: ApplicationContainer com os serviços
            update_interval: Intervalo de atualização em segundos
        """
        super().__init__()
        self.container = container
        self.update_interval = update_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
    
    def run(self):
        """Executa a coleta contínua de estatísticas."""
        try:
            self.running = True
            
            # Obter serviço
            stats_service = self.container.system_stats_service()
            
            # Verificar e inicializar serviço se necessário
            try:
                # Verificar se o serviço tem os atributos necessários
                if not hasattr(stats_service, 'metrics_history') or not hasattr(stats_service, 'current_metrics'):
                    self.logger.info("Inicializando SystemStatsService...")
                    stats_service.initialize()
                
                # Verificar se o método get_current_metrics existe
                if not hasattr(stats_service, 'get_current_metrics'):
                    raise AttributeError("SystemStatsService não possui método get_current_metrics")
                    
            except Exception as init_error:
                self.logger.error(f"Erro ao inicializar SystemStatsService: {init_error}")
                self.error_occurred.emit(f"Falha na inicialização do serviço: {init_error}")
                return
            while self.running:
                try:
                    # Coletar métricas atuais - corrigido método inexistente
                    current_metrics = stats_service.get_current_metrics()
                    
                    # Obter dados históricos
                    historical_data = stats_service.get_historical_data(hours=1)
                    
                    # Gerar resumo de performance
                    performance_summary = stats_service.get_performance_summary()
                    
                    # Verificar alertas
                    alerts = stats_service.check_alerts()
                    
                    # Combinar dados
                    stats_data = {
                        'current': current_metrics,
                        'historical': historical_data,
                        'performance': performance_summary,
                        'alerts': alerts,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Emitir dados
                    self.stats_updated.emit(stats_data)
                    
                    # Emitir alertas se houver
                    for alert in alerts:
                        self.alert_triggered.emit(alert.get('type', 'Unknown'), alert.get('message', ''))
                    
                    # Aguardar próxima atualização
                    self.msleep(self.update_interval * 1000)
                    
                except Exception as e:
                    self.logger.error(f"Erro na coleta de estatísticas: {e}")
                    self.error_occurred.emit(str(e))
                    self.msleep(5000)  # Aguardar 5 segundos antes de tentar novamente
            
        except Exception as e:
            self.logger.error(f"Erro fatal no worker de estatísticas: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
    
    def stop(self):
        """Para a execução do worker."""
        self.running = False
        if self.isRunning():
            self.quit()
            self.wait(5000)  # Aguarda até 5 segundos


class MetricsChart(QWidget):
    """Widget personalizado para exibir gráficos de métricas."""
    
    def __init__(self, title: str, max_points: int = 60, parent=None):
        """Inicializa o gráfico de métricas.
        
        Args:
            title: Título do gráfico
            max_points: Número máximo de pontos a exibir
            parent: Widget pai
        """
        super().__init__(parent)
        
        self.title = title
        self.max_points = max_points
        self.data_points = []
        self.max_value = 100
        self.min_value = 0
        
        self.setMinimumSize(300, 150)
        self.setMaximumHeight(200)
    
    def add_data_point(self, value: float):
        """Adiciona um ponto de dados ao gráfico.
        
        Args:
            value: Valor a ser adicionado
        """
        self.data_points.append(value)
        
        # Manter apenas os últimos max_points
        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)
        
        # Atualizar valores min/max
        if self.data_points:
            self.max_value = max(max(self.data_points), 100)
            self.min_value = min(min(self.data_points), 0)
        
        self.update()
    
    def clear_data(self):
        """Limpa todos os dados do gráfico."""
        self.data_points.clear()
        self.max_value = 100
        self.min_value = 0
        self.update()
    
    def paintEvent(self, event):
        """Desenha o gráfico."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Configurar área de desenho
        rect = self.rect()
        margin = 20
        chart_rect = rect.adjusted(margin, margin, -margin, -margin)
        
        # Desenhar fundo
        painter.fillRect(rect, QColor(250, 250, 250))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(chart_rect)
        
        # Desenhar título
        painter.setPen(QPen(QColor(50, 50, 50), 1))
        title_rect = rect.adjusted(0, 0, 0, -rect.height() + margin)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)
        
        if not self.data_points:
            # Desenhar mensagem "Sem dados"
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(chart_rect, Qt.AlignCenter, "Aguardando dados...")
            return
        
        # Calcular escala
        value_range = self.max_value - self.min_value
        if value_range == 0:
            value_range = 1
        
        # Desenhar linhas de grade
        painter.setPen(QPen(QColor(230, 230, 230), 1))
        for i in range(1, 5):
            y = chart_rect.top() + (chart_rect.height() * i / 5)
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)
        
        # Desenhar dados
        if len(self.data_points) > 1:
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            
            points = []
            for i, value in enumerate(self.data_points):
                x = chart_rect.left() + (chart_rect.width() * i / (len(self.data_points) - 1))
                y = chart_rect.bottom() - ((value - self.min_value) / value_range * chart_rect.height())
                points.append((x, y))
            
            # Desenhar linha
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
            
            # Desenhar pontos
            painter.setBrush(QBrush(QColor(0, 120, 215)))
            for x, y in points:
                painter.drawEllipse(x - 2, y - 2, 4, 4)
        
        # Desenhar valores min/max
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawText(chart_rect.adjusted(-margin, 0, 0, 0), Qt.AlignLeft | Qt.AlignTop, f"{self.max_value:.1f}")
        painter.drawText(chart_rect.adjusted(-margin, 0, 0, 0), Qt.AlignLeft | Qt.AlignBottom, f"{self.min_value:.1f}")


class SystemStatsWidget(QWidget):
    """Widget para visualização de estatísticas do sistema em tempo real."""
    
    # Signals
    monitoring_started = Signal()
    monitoring_stopped = Signal()
    alert_acknowledged = Signal(str)
    
    def __init__(self, container, parent: QWidget = None):
        """Inicializa o widget de estatísticas do sistema.
        
        Args:
            container: ApplicationContainer com os serviços
            parent: Widget pai (opcional)
        """
        super().__init__(parent)
        
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Worker para coleta de estatísticas
        self.stats_worker = None
        
        # Estado do monitoramento
        self.monitoring_active = False
        
        # Dados atuais
        self.current_stats = {}
        self.alerts_list = []
        
        # Configurar UI
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Configura a interface do usuário."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título e controles
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Estatísticas do Sistema")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Controles de monitoramento
        header_layout.addWidget(QLabel("Intervalo:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1 segundo", "5 segundos", "10 segundos", "30 segundos"])
        self.interval_combo.setCurrentIndex(1)  # 5 segundos por padrão
        header_layout.addWidget(self.interval_combo)
        
        self.start_stop_button = QPushButton("Iniciar Monitoramento")
        self.start_stop_button.clicked.connect(self._toggle_monitoring)
        header_layout.addWidget(self.start_stop_button)
        
        layout.addLayout(header_layout)
        
        # Tabs para organizar conteúdo
        self.tab_widget = QTabWidget()
        
        # Tab 1: Métricas em Tempo Real
        self.realtime_tab = self._create_realtime_tab()
        self.tab_widget.addTab(self.realtime_tab, "Tempo Real")
        
        # Tab 2: Gráficos
        self.charts_tab = self._create_charts_tab()
        self.tab_widget.addTab(self.charts_tab, "Gráficos")
        
        # Tab 3: Alertas
        self.alerts_tab = self._create_alerts_tab()
        self.tab_widget.addTab(self.alerts_tab, "Alertas")
        
        # Tab 4: Configurações
        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Configurações")
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("Monitoramento parado. Clique em 'Iniciar Monitoramento' para começar.")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
    
    def _create_realtime_tab(self) -> QWidget:
        """Cria a tab de métricas em tempo real."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Métricas principais
        main_metrics_group = QGroupBox("Métricas Principais")
        main_layout = QGridLayout(main_metrics_group)
        
        # CPU
        main_layout.addWidget(QLabel("CPU:"), 0, 0)
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setTextVisible(True)
        main_layout.addWidget(self.cpu_progress, 0, 1)
        self.cpu_value_label = QLabel("0%")
        main_layout.addWidget(self.cpu_value_label, 0, 2)
        
        # Memória
        main_layout.addWidget(QLabel("Memória:"), 1, 0)
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        self.memory_progress.setTextVisible(True)
        main_layout.addWidget(self.memory_progress, 1, 1)
        self.memory_value_label = QLabel("0%")
        main_layout.addWidget(self.memory_value_label, 1, 2)
        
        # Disco
        main_layout.addWidget(QLabel("Disco:"), 2, 0)
        self.disk_progress = QProgressBar()
        self.disk_progress.setRange(0, 100)
        self.disk_progress.setTextVisible(True)
        main_layout.addWidget(self.disk_progress, 2, 1)
        self.disk_value_label = QLabel("0%")
        main_layout.addWidget(self.disk_value_label, 2, 2)
        
        main_layout.setColumnStretch(1, 1)
        layout.addWidget(main_metrics_group)
        
        # Métricas detalhadas
        details_group = QGroupBox("Detalhes do Sistema")
        details_layout = QGridLayout(details_group)
        
        # Informações de CPU
        details_layout.addWidget(QLabel("Núcleos de CPU:"), 0, 0)
        self.cpu_cores_label = QLabel("-")
        details_layout.addWidget(self.cpu_cores_label, 0, 1)
        
        details_layout.addWidget(QLabel("Frequência CPU:"), 1, 0)
        self.cpu_freq_label = QLabel("-")
        details_layout.addWidget(self.cpu_freq_label, 1, 1)
        
        # Informações de memória
        details_layout.addWidget(QLabel("Memória Total:"), 2, 0)
        self.memory_total_label = QLabel("-")
        details_layout.addWidget(self.memory_total_label, 2, 1)
        
        details_layout.addWidget(QLabel("Memória Disponível:"), 3, 0)
        self.memory_available_label = QLabel("-")
        details_layout.addWidget(self.memory_available_label, 3, 1)
        
        # Informações de disco
        details_layout.addWidget(QLabel("Espaço Total:"), 4, 0)
        self.disk_total_label = QLabel("-")
        details_layout.addWidget(self.disk_total_label, 4, 1)
        
        details_layout.addWidget(QLabel("Espaço Livre:"), 5, 0)
        self.disk_free_label = QLabel("-")
        details_layout.addWidget(self.disk_free_label, 5, 1)
        
        details_layout.setColumnStretch(1, 1)
        layout.addWidget(details_group)
        
        # Performance summary
        performance_group = QGroupBox("Resumo de Performance")
        performance_layout = QVBoxLayout(performance_group)
        
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(100)
        self.performance_text.setPlainText("Aguardando dados de performance...")
        performance_layout.addWidget(self.performance_text)
        
        layout.addWidget(performance_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_charts_tab(self) -> QWidget:
        """Cria a tab de gráficos."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Gráficos de métricas
        charts_layout = QGridLayout()
        
        # Gráfico de CPU
        self.cpu_chart = MetricsChart("Uso de CPU (%)")
        charts_layout.addWidget(self.cpu_chart, 0, 0)
        
        # Gráfico de Memória
        self.memory_chart = MetricsChart("Uso de Memória (%)")
        charts_layout.addWidget(self.memory_chart, 0, 1)
        
        # Gráfico de Disco
        self.disk_chart = MetricsChart("Uso de Disco (%)")
        charts_layout.addWidget(self.disk_chart, 1, 0)
        
        # Gráfico de Rede (placeholder)
        self.network_chart = MetricsChart("Atividade de Rede")
        charts_layout.addWidget(self.network_chart, 1, 1)
        
        layout.addLayout(charts_layout)
        
        # Controles dos gráficos
        controls_layout = QHBoxLayout()
        
        clear_button = QPushButton("Limpar Gráficos")
        clear_button.clicked.connect(self._clear_charts)
        controls_layout.addWidget(clear_button)
        
        controls_layout.addStretch()
        
        export_button = QPushButton("Exportar Dados")
        export_button.clicked.connect(self._export_chart_data)
        controls_layout.addWidget(export_button)
        
        layout.addLayout(controls_layout)
        
        return widget
    
    def _create_alerts_tab(self) -> QWidget:
        """Cria a tab de alertas."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Lista de alertas
        alerts_group = QGroupBox("Alertas Ativos")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_list_widget = QListWidget()
        self.alerts_list_widget.setAlternatingRowColors(True)
        alerts_layout.addWidget(self.alerts_list_widget)
        
        # Botões de ação
        alerts_buttons_layout = QHBoxLayout()
        
        self.acknowledge_button = QPushButton("Reconhecer Selecionado")
        self.acknowledge_button.setEnabled(False)
        self.acknowledge_button.clicked.connect(self._acknowledge_alert)
        alerts_buttons_layout.addWidget(self.acknowledge_button)
        
        self.clear_all_button = QPushButton("Limpar Todos")
        self.clear_all_button.clicked.connect(self._clear_all_alerts)
        alerts_buttons_layout.addWidget(self.clear_all_button)
        
        alerts_buttons_layout.addStretch()
        alerts_layout.addLayout(alerts_buttons_layout)
        
        layout.addWidget(alerts_group)
        
        # Histórico de alertas
        history_group = QGroupBox("Histórico de Alertas")
        history_layout = QVBoxLayout(history_group)
        
        self.alerts_history = QTextEdit()
        self.alerts_history.setReadOnly(True)
        self.alerts_history.setMaximumHeight(150)
        history_layout.addWidget(self.alerts_history)
        
        layout.addWidget(history_group)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Cria a tab de configurações."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Configurações de alertas
        alerts_config_group = QGroupBox("Configurações de Alertas")
        alerts_config_layout = QGridLayout(alerts_config_group)
        
        # Limite de CPU
        alerts_config_layout.addWidget(QLabel("Alerta CPU (%):"), 0, 0)
        self.cpu_threshold_slider = QSlider(Qt.Horizontal)
        self.cpu_threshold_slider.setRange(50, 95)
        self.cpu_threshold_slider.setValue(80)
        self.cpu_threshold_slider.valueChanged.connect(self._update_cpu_threshold_label)
        alerts_config_layout.addWidget(self.cpu_threshold_slider, 0, 1)
        self.cpu_threshold_label = QLabel("80%")
        alerts_config_layout.addWidget(self.cpu_threshold_label, 0, 2)
        
        # Limite de Memória
        alerts_config_layout.addWidget(QLabel("Alerta Memória (%):"), 1, 0)
        self.memory_threshold_slider = QSlider(Qt.Horizontal)
        self.memory_threshold_slider.setRange(50, 95)
        self.memory_threshold_slider.setValue(85)
        self.memory_threshold_slider.valueChanged.connect(self._update_memory_threshold_label)
        alerts_config_layout.addWidget(self.memory_threshold_slider, 1, 1)
        self.memory_threshold_label = QLabel("85%")
        alerts_config_layout.addWidget(self.memory_threshold_label, 1, 2)
        
        # Limite de Disco
        alerts_config_layout.addWidget(QLabel("Alerta Disco (%):"), 2, 0)
        self.disk_threshold_slider = QSlider(Qt.Horizontal)
        self.disk_threshold_slider.setRange(70, 95)
        self.disk_threshold_slider.setValue(90)
        self.disk_threshold_slider.valueChanged.connect(self._update_disk_threshold_label)
        alerts_config_layout.addWidget(self.disk_threshold_slider, 2, 1)
        self.disk_threshold_label = QLabel("90%")
        alerts_config_layout.addWidget(self.disk_threshold_label, 2, 2)
        
        alerts_config_layout.setColumnStretch(1, 1)
        layout.addWidget(alerts_config_group)
        
        # Configurações de monitoramento
        monitoring_config_group = QGroupBox("Configurações de Monitoramento")
        monitoring_config_layout = QGridLayout(monitoring_config_group)
        
        # Auto-start
        self.auto_start_checkbox = QCheckBox("Iniciar monitoramento automaticamente")
        monitoring_config_layout.addWidget(self.auto_start_checkbox, 0, 0, 1, 2)
        
        # Histórico
        monitoring_config_layout.addWidget(QLabel("Manter histórico (horas):"), 1, 0)
        self.history_hours_spinbox = QSpinBox()
        self.history_hours_spinbox.setRange(1, 24)
        self.history_hours_spinbox.setValue(6)
        monitoring_config_layout.addWidget(self.history_hours_spinbox, 1, 1)
        
        monitoring_config_layout.setColumnStretch(1, 1)
        layout.addWidget(monitoring_config_group)
        
        # Botões de ação
        settings_buttons_layout = QHBoxLayout()
        settings_buttons_layout.addStretch()
        
        self.apply_settings_button = QPushButton("Aplicar Configurações")
        self.apply_settings_button.clicked.connect(self._apply_settings)
        settings_buttons_layout.addWidget(self.apply_settings_button)
        
        self.reset_settings_button = QPushButton("Restaurar Padrões")
        self.reset_settings_button.clicked.connect(self._reset_settings)
        settings_buttons_layout.addWidget(self.reset_settings_button)
        
        layout.addLayout(settings_buttons_layout)
        layout.addStretch()
        
        return widget
    
    def _setup_connections(self):
        """Configura as conexões de sinais."""
        # Conectar mudanças de seleção na lista de alertas
        self.alerts_list_widget.itemSelectionChanged.connect(self._on_alert_selection_changed)
    
    def _toggle_monitoring(self):
        """Alterna o estado do monitoramento."""
        if self.monitoring_active:
            self._stop_monitoring()
        else:
            self._start_monitoring()
    
    def _start_monitoring(self):
        """Inicia o monitoramento de estatísticas."""
        try:
            # Parar worker anterior se estiver rodando
            if self.stats_worker and self.stats_worker.isRunning():
                self.stats_worker.stop()
            
            # Obter intervalo selecionado
            interval_text = self.interval_combo.currentText()
            interval_map = {
                "1 segundo": 1,
                "5 segundos": 5,
                "10 segundos": 10,
                "30 segundos": 30
            }
            interval = interval_map.get(interval_text, 5)
            
            # Criar novo worker
            self.stats_worker = SystemStatsWorker(self.container, interval)
            self.stats_worker.stats_updated.connect(self._on_stats_updated)
            self.stats_worker.alert_triggered.connect(self._on_alert_triggered)
            self.stats_worker.error_occurred.connect(self._on_error_occurred)
            
            # Atualizar UI
            self.monitoring_active = True
            self.start_stop_button.setText("Parar Monitoramento")
            self.interval_combo.setEnabled(False)
            self.status_label.setText("Monitoramento ativo...")
            
            # Emitir sinal
            self.monitoring_started.emit()
            
            # Iniciar worker
            self.stats_worker.start()
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar monitoramento: {e}")
            self._on_error_occurred(str(e))
    
    def _stop_monitoring(self):
        """Para o monitoramento de estatísticas."""
        try:
            # Parar worker
            if self.stats_worker and self.stats_worker.isRunning():
                self.stats_worker.stop()
            
            # Atualizar UI
            self.monitoring_active = False
            self.start_stop_button.setText("Iniciar Monitoramento")
            self.interval_combo.setEnabled(True)
            self.status_label.setText("Monitoramento parado.")
            
            # Emitir sinal
            self.monitoring_stopped.emit()
            
        except Exception as e:
            self.logger.error(f"Erro ao parar monitoramento: {e}")
    
    def _on_stats_updated(self, stats_data: Dict[str, Any]):
        """Callback chamado quando as estatísticas são atualizadas.
        
        Args:
            stats_data: Dados de estatísticas
        """
        try:
            self.current_stats = stats_data
            
            # Atualizar métricas em tempo real
            current_metrics = stats_data.get('current', {})
            self._update_realtime_metrics(current_metrics)
            
            # Atualizar gráficos
            self._update_charts(current_metrics)
            
            # Atualizar resumo de performance
            performance_summary = stats_data.get('performance', {})
            self._update_performance_summary(performance_summary)
            
            # Atualizar status
            timestamp = stats_data.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                    self.status_label.setText(f"Última atualização: {time_str}")
                except:
                    self.status_label.setText("Monitoramento ativo...")
            
        except Exception as e:
            self.logger.error(f"Erro ao processar estatísticas: {e}")
    
    def _update_realtime_metrics(self, metrics: Dict[str, Any]):
        """Atualiza as métricas em tempo real.
        
        Args:
            metrics: Dicionário com métricas atuais
        """
        # CPU
        cpu_percent = metrics.get('cpu_percent', 0)
        self.cpu_progress.setValue(int(cpu_percent))
        self.cpu_value_label.setText(f"{cpu_percent:.1f}%")
        
        # Definir cor da barra baseada no uso
        if cpu_percent > 80:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: #dc3545; }")
        elif cpu_percent > 60:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffc107; }")
        else:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: #28a745; }")
        
        # Memória
        memory_percent = metrics.get('memory_percent', 0)
        self.memory_progress.setValue(int(memory_percent))
        self.memory_value_label.setText(f"{memory_percent:.1f}%")
        
        if memory_percent > 85:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #dc3545; }")
        elif memory_percent > 70:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffc107; }")
        else:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #28a745; }")
        
        # Disco
        disk_percent = metrics.get('disk_percent', 0)
        self.disk_progress.setValue(int(disk_percent))
        self.disk_value_label.setText(f"{disk_percent:.1f}%")
        
        if disk_percent > 90:
            self.disk_progress.setStyleSheet("QProgressBar::chunk { background-color: #dc3545; }")
        elif disk_percent > 80:
            self.disk_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffc107; }")
        else:
            self.disk_progress.setStyleSheet("QProgressBar::chunk { background-color: #28a745; }")
        
        # Detalhes
        self.cpu_cores_label.setText(str(metrics.get('cpu_cores', '-')))
        
        cpu_freq = metrics.get('cpu_freq_mhz', 0)
        if cpu_freq > 0:
            self.cpu_freq_label.setText(f"{cpu_freq:.0f} MHz")
        else:
            self.cpu_freq_label.setText("-")
        
        memory_total = metrics.get('memory_total_gb', 0)
        if memory_total > 0:
            self.memory_total_label.setText(f"{memory_total:.1f} GB")
        else:
            self.memory_total_label.setText("-")
        
        memory_available = metrics.get('memory_available_gb', 0)
        if memory_available > 0:
            self.memory_available_label.setText(f"{memory_available:.1f} GB")
        else:
            self.memory_available_label.setText("-")
        
        disk_total = metrics.get('disk_total_gb', 0)
        if disk_total > 0:
            self.disk_total_label.setText(f"{disk_total:.1f} GB")
        else:
            self.disk_total_label.setText("-")
        
        disk_free = metrics.get('disk_free_gb', 0)
        if disk_free > 0:
            self.disk_free_label.setText(f"{disk_free:.1f} GB")
        else:
            self.disk_free_label.setText("-")
    
    def _update_charts(self, metrics: Dict[str, Any]):
        """Atualiza os gráficos com novos dados.
        
        Args:
            metrics: Dicionário com métricas atuais
        """
        self.cpu_chart.add_data_point(metrics.get('cpu_percent', 0))
        self.memory_chart.add_data_point(metrics.get('memory_percent', 0))
        self.disk_chart.add_data_point(metrics.get('disk_percent', 0))
        
        # Network placeholder (pode ser implementado futuramente)
        self.network_chart.add_data_point(0)
    
    def _update_performance_summary(self, performance: Dict[str, Any]):
        """Atualiza o resumo de performance.
        
        Args:
            performance: Dicionário com resumo de performance
        """
        if not performance:
            return
        
        summary_text = "Resumo de Performance:\n\n"
        
        # CPU
        cpu_avg = performance.get('cpu_average', 0)
        cpu_max = performance.get('cpu_max', 0)
        summary_text += f"CPU - Média: {cpu_avg:.1f}%, Máximo: {cpu_max:.1f}%\n"
        
        # Memória
        memory_avg = performance.get('memory_average', 0)
        memory_max = performance.get('memory_max', 0)
        summary_text += f"Memória - Média: {memory_avg:.1f}%, Máximo: {memory_max:.1f}%\n"
        
        # Disco
        disk_avg = performance.get('disk_average', 0)
        disk_max = performance.get('disk_max', 0)
        summary_text += f"Disco - Média: {disk_avg:.1f}%, Máximo: {disk_max:.1f}%\n\n"
        
        # Status geral
        health_status = performance.get('health_status', 'Unknown')
        summary_text += f"Status Geral: {health_status}"
        
        self.performance_text.setPlainText(summary_text)
    
    def _on_alert_triggered(self, alert_type: str, message: str):
        """Callback chamado quando um alerta é disparado.
        
        Args:
            alert_type: Tipo do alerta
            message: Mensagem do alerta
        """
        # Adicionar à lista de alertas
        timestamp = datetime.now().strftime('%H:%M:%S')
        alert_text = f"[{timestamp}] {alert_type}: {message}"
        
        # Adicionar à lista visual
        item = QListWidgetItem(alert_text)
        
        # Definir cor baseada no tipo
        if alert_type.lower() in ['critical', 'crítico']:
            item.setBackground(QColor(255, 200, 200))
        elif alert_type.lower() in ['warning', 'aviso']:
            item.setBackground(QColor(255, 255, 200))
        else:
            item.setBackground(QColor(200, 200, 255))
        
        self.alerts_list_widget.addItem(item)
        
        # Adicionar ao histórico
        current_history = self.alerts_history.toPlainText()
        new_history = alert_text + "\n" + current_history
        
        # Limitar histórico a 1000 caracteres
        if len(new_history) > 1000:
            new_history = new_history[:1000] + "..."
        
        self.alerts_history.setPlainText(new_history)
        
        # Scroll para o topo da lista
        self.alerts_list_widget.scrollToTop()
    
    def _on_alert_selection_changed(self):
        """Callback chamado quando a seleção de alertas muda."""
        has_selection = len(self.alerts_list_widget.selectedItems()) > 0
        self.acknowledge_button.setEnabled(has_selection)
    
    def _acknowledge_alert(self):
        """Reconhece o alerta selecionado."""
        selected_items = self.alerts_list_widget.selectedItems()
        for item in selected_items:
            # Marcar como reconhecido
            text = item.text()
            if not text.startswith("✓"):
                item.setText("✓ " + text)
                item.setBackground(QColor(200, 255, 200))
            
            # Emitir sinal
            self.alert_acknowledged.emit(text)
    
    def _clear_all_alerts(self):
        """Limpa todos os alertas."""
        reply = QMessageBox.question(
            self,
            "Limpar Alertas",
            "Tem certeza que deseja limpar todos os alertas?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.alerts_list_widget.clear()
            self.alerts_history.clear()
    
    def _clear_charts(self):
        """Limpa todos os gráficos."""
        self.cpu_chart.clear_data()
        self.memory_chart.clear_data()
        self.disk_chart.clear_data()
        self.network_chart.clear_data()
    
    def _export_chart_data(self):
        """Exporta os dados dos gráficos."""
        try:
            # Implementação simplificada
            QMessageBox.information(
                self,
                "Exportar Dados",
                "Funcionalidade de exportação será implementada em versão futura."
            )
        except Exception as e:
            self.logger.error(f"Erro ao exportar dados: {e}")
    
    def _update_cpu_threshold_label(self, value: int):
        """Atualiza o label do limite de CPU."""
        self.cpu_threshold_label.setText(f"{value}%")
    
    def _update_memory_threshold_label(self, value: int):
        """Atualiza o label do limite de memória."""
        self.memory_threshold_label.setText(f"{value}%")
    
    def _update_disk_threshold_label(self, value: int):
        """Atualiza o label do limite de disco."""
        self.disk_threshold_label.setText(f"{value}%")
    
    def _apply_settings(self):
        """Aplica as configurações atuais."""
        try:
            settings = {
                'cpu_threshold': self.cpu_threshold_slider.value(),
                'memory_threshold': self.memory_threshold_slider.value(),
                'disk_threshold': self.disk_threshold_slider.value(),
                'auto_start': self.auto_start_checkbox.isChecked(),
                'history_hours': self.history_hours_spinbox.value()
            }
            
            # Aqui você pode salvar as configurações ou aplicá-las ao serviço
            
            QMessageBox.information(
                self,
                "Configurações",
                "Configurações aplicadas com sucesso."
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao aplicar configurações: {e}")
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao aplicar configurações:\n{str(e)}"
            )
    
    def _reset_settings(self):
        """Restaura as configurações padrão."""
        self.cpu_threshold_slider.setValue(80)
        self.memory_threshold_slider.setValue(85)
        self.disk_threshold_slider.setValue(90)
        self.auto_start_checkbox.setChecked(False)
        self.history_hours_spinbox.setValue(6)
        
        QMessageBox.information(
            self,
            "Configurações",
            "Configurações restauradas para os valores padrão."
        )
    
    def _on_error_occurred(self, error_message: str):
        """Callback chamado quando ocorre um erro.
        
        Args:
            error_message: Mensagem de erro
        """
        self.logger.error(f"Erro no SystemStatsWidget: {error_message}")
        
        # Parar monitoramento em caso de erro
        if self.monitoring_active:
            self._stop_monitoring()
        
        # Atualizar status
        self.status_label.setText(f"Erro: {error_message}")
        
        # Mostrar mensagem de erro
        QMessageBox.warning(
            self,
            "Erro",
            f"Erro no monitoramento de estatísticas:\n{error_message}"
        )
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Retorna as estatísticas atuais.
        
        Returns:
            Dicionário com as estatísticas atuais
        """
        return self.current_stats.copy()
    
    def is_monitoring_active(self) -> bool:
        """Verifica se o monitoramento está ativo.
        
        Returns:
            True se o monitoramento estiver ativo
        """
        return self.monitoring_active
    
    def closeEvent(self, event):
        """Evento chamado ao fechar o widget."""
        # Parar monitoramento
        if self.monitoring_active:
            self._stop_monitoring()
        
        super().closeEvent(event)