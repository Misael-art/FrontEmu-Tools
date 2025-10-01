"""
System Stats Widget

Widget modernizado para monitoramento de estatísticas do sistema em tempo real
seguindo as especificações de UI/UX e Clean Architecture.
"""

from typing import Optional, List, Dict, Any, Deque
from collections import deque
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton, QProgressBar,
    QGroupBox, QListWidget, QListWidgetItem, QComboBox,
    QCheckBox, QSpinBox, QLineEdit, QTextEdit, QSplitter,
    QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon, QPen
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis

from ...infrastructure import DependencyContainer
from ...domain.entities import SystemMetrics, SystemAlert, AlertSeverity
from ...app.logging_config import get_logger


class SystemMonitorWorker(QThread):
    """Worker thread para monitoramento contínuo do sistema."""
    
    metrics_updated = Signal(object)  # SystemMetrics
    alert_generated = Signal(object)  # SystemAlert
    error_occurred = Signal(str)

    def __init__(self, container: DependencyContainer):
        super().__init__()
        self.container = container
        self.logger = get_logger(__name__)
        self.running = False

    def run(self):
        """Executa monitoramento contínuo."""
        self.running = True
        
        try:
            # Obter use case de monitoramento
            monitor_use_case = self.container.get_monitor_system_performance_use_case()
            
            while self.running:
                # Coletar métricas
                result = monitor_use_case.execute()
                
                if result.success:
                    metrics = result.data
                    self.metrics_updated.emit(metrics)
                    
                    # Verificar alertas
                    self._check_alerts(metrics)
                else:
                    self.error_occurred.emit(result.error_message)
                
                # Aguardar próxima coleta (2 segundos)
                self.msleep(2000)
                
        except Exception as e:
            self.logger.error(f"Erro no monitoramento: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        """Para o monitoramento."""
        self.running = False

    def _check_alerts(self, metrics: SystemMetrics):
        """Verifica se há alertas baseados nas métricas."""
        # CPU alto
        if metrics.cpu_usage > 90:
            alert = SystemAlert(
                id="cpu_high",
                message=f"Uso de CPU alto: {metrics.cpu_usage:.1f}%",
                severity=AlertSeverity.HIGH,
                component="CPU",
                details={"cpu_usage": metrics.cpu_usage}
            )
            self.alert_generated.emit(alert)
        
        # Memória alta
        if metrics.memory_usage > 85:
            alert = SystemAlert(
                id="memory_high",
                message=f"Uso de memória alto: {metrics.memory_usage:.1f}%",
                severity=AlertSeverity.HIGH,
                component="Memory",
                details={"memory_usage": metrics.memory_usage}
            )
            self.alert_generated.emit(alert)
        
        # Disco alto
        if metrics.disk_usage > 90:
            alert = SystemAlert(
                id="disk_high",
                message=f"Uso de disco alto: {metrics.disk_usage:.1f}%",
                severity=AlertSeverity.MEDIUM,
                component="Disk",
                details={"disk_usage": metrics.disk_usage}
            )
            self.alert_generated.emit(alert)


class MetricCard(QFrame):
    """Card para exibir uma métrica específica."""

    def __init__(self, title: str, icon: str = "📊", unit: str = "%", parent=None):
        """Inicializa o card de métrica."""
        super().__init__(parent)
        self.title = title
        self.icon = icon
        self.unit = unit
        self.current_value = 0.0
        self.history: Deque[float] = deque(maxlen=60)  # 2 minutos de histórico
        
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """Configura a interface do card."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        
        # Ícone
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("font-size: 20px;")
        header_layout.addWidget(icon_label)
        
        # Título
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Valor atual
        self.value_label = QLabel("0.0%")
        self.value_label.setStyleSheet("""
            QLabel {
                color: #32CD32;
                font-size: 24px;
                font-weight: bold;
                margin: 8px 0;
            }
        """)
        layout.addWidget(self.value_label)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #32CD32;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Estatísticas
        stats_layout = QHBoxLayout()
        
        self.min_label = QLabel("Min: 0.0")
        self.min_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        stats_layout.addWidget(self.min_label)
        
        stats_layout.addStretch()
        
        self.max_label = QLabel("Max: 0.0")
        self.max_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        stats_layout.addWidget(self.max_label)
        
        layout.addLayout(stats_layout)

    def update_value(self, value: float):
        """Atualiza o valor da métrica."""
        self.current_value = value
        self.history.append(value)
        
        # Atualizar display
        self.value_label.setText(f"{value:.1f}{self.unit}")
        self.progress_bar.setValue(int(value))
        
        # Atualizar cor baseada no valor
        self._update_color(value)
        
        # Atualizar estatísticas
        if self.history:
            min_val = min(self.history)
            max_val = max(self.history)
            self.min_label.setText(f"Min: {min_val:.1f}")
            self.max_label.setText(f"Max: {max_val:.1f}")

    def _update_color(self, value: float):
        """Atualiza cor baseada no valor."""
        if value < 50:
            color = "#32CD32"  # Verde
        elif value < 80:
            color = "#ffc107"  # Amarelo
        else:
            color = "#dc3545"  # Vermelho
        
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 24px;
                font-weight: bold;
                margin: 8px 0;
            }}
        """)
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

    def _apply_style(self):
        """Aplica estilo ao card."""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                margin: 4px;
            }
            QFrame:hover {
                border-color: #32CD32;
                box-shadow: 0 4px 12px rgba(50, 205, 50, 0.15);
            }
        """)


class ProcessTable(QTableWidget):
    """Tabela para exibir processos do sistema."""

    def __init__(self, parent=None):
        """Inicializa a tabela de processos."""
        super().__init__(parent)
        
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Processo", "PID", "CPU %", "Memória"])
        
        # Configurar aparência
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                gridline-color: #e9ecef;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f8f9fa;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #32CD32;
            }
        """)
        
        # Configurar colunas
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 80)
        
        # Configurar seleção
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)

    def update_processes(self, processes: List[Dict[str, Any]]):
        """Atualiza lista de processos."""
        self.setRowCount(len(processes))
        
        for row, process in enumerate(processes):
            # Nome do processo
            name_item = QTableWidgetItem(process.get("name", ""))
            self.setItem(row, 0, name_item)
            
            # PID
            pid_item = QTableWidgetItem(str(process.get("pid", "")))
            self.setItem(row, 1, pid_item)
            
            # CPU
            cpu_item = QTableWidgetItem(f"{process.get('cpu_percent', 0):.1f}%")
            self.setItem(row, 2, cpu_item)
            
            # Memória
            memory_mb = process.get('memory_mb', 0)
            memory_item = QTableWidgetItem(f"{memory_mb:.1f} MB")
            self.setItem(row, 3, memory_item)


class AlertsPanel(QFrame):
    """Painel para exibir alertas do sistema."""

    def __init__(self, parent=None):
        """Inicializa o painel de alertas."""
        super().__init__(parent)
        
        self.alerts: List[SystemAlert] = []
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """Configura a interface do painel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🚨 Alertas do Sistema")
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Botão para limpar alertas
        clear_button = QPushButton("🗑️")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        clear_button.clicked.connect(self.clear_alerts)
        header_layout.addWidget(clear_button)
        
        layout.addLayout(header_layout)

        # Lista de alertas
        self.alerts_list = QListWidget()
        self.alerts_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-color: #1976d2;
            }
        """)
        layout.addWidget(self.alerts_list)

        # Mensagem quando não há alertas
        self.no_alerts_label = QLabel("✅ Nenhum alerta ativo")
        self.no_alerts_label.setAlignment(Qt.AlignCenter)
        self.no_alerts_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-size: 12px;
                padding: 20px;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.no_alerts_label)
        
        self._update_visibility()

    def add_alert(self, alert: SystemAlert):
        """Adiciona um novo alerta."""
        # Evitar alertas duplicados
        if any(a.id == alert.id for a in self.alerts):
            return
        
        self.alerts.append(alert)
        self._update_alerts_display()

    def clear_alerts(self):
        """Limpa todos os alertas."""
        self.alerts.clear()
        self._update_alerts_display()

    def _update_alerts_display(self):
        """Atualiza exibição dos alertas."""
        self.alerts_list.clear()
        
        for alert in self.alerts:
            item = QListWidgetItem()
            
            # Ícone baseado na severidade
            severity_icons = {
                AlertSeverity.LOW: "🟡",
                AlertSeverity.MEDIUM: "🟠",
                AlertSeverity.HIGH: "🔴",
                AlertSeverity.CRITICAL: "💀"
            }
            
            icon = severity_icons.get(alert.severity, "ℹ️")
            text = f"{icon} {alert.message}"
            
            item.setText(text)
            item.setData(Qt.UserRole, alert)
            
            self.alerts_list.addItem(item)
        
        self._update_visibility()

    def _update_visibility(self):
        """Atualiza visibilidade dos elementos."""
        has_alerts = len(self.alerts) > 0
        self.alerts_list.setVisible(has_alerts)
        self.no_alerts_label.setVisible(not has_alerts)

    def _apply_style(self):
        """Aplica estilo ao painel."""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
            }
        """)


class SystemStatsWidget(QWidget):
    """Widget modernizado para estatísticas do sistema."""

    # Sinais
    metrics_updated = Signal(object)  # SystemMetrics
    alert_generated = Signal(object)  # SystemAlert

    def __init__(self, container: DependencyContainer, parent=None):
        """Inicializa o widget de estatísticas."""
        super().__init__(parent)
        
        self.container = container
        self.logger = get_logger(__name__)
        
        # Estado
        self.monitor_worker: Optional[SystemMonitorWorker] = None
        self.metric_cards: Dict[str, MetricCard] = {}
        self.is_monitoring = False
        
        self._setup_ui()
        self._apply_modern_style()

    def _setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        self._create_header(layout)

        # Splitter principal
        splitter = QSplitter(Qt.Vertical)
        
        # Área superior - Métricas principais
        self._create_metrics_panel(splitter)
        
        # Área inferior - Processos e alertas
        self._create_details_panel(splitter)
        
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)

    def _create_header(self, layout: QVBoxLayout):
        """Cria header do widget."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #32CD32, stop:1 #28a428);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 16, 20, 16)

        # Título
        title_label = QLabel("📊 Monitoramento do Sistema")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)

        # Espaçador
        header_layout.addStretch()

        # Status do monitoramento
        self.status_label = QLabel("⏸️ Parado")
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: 500;
                padding: 4px 8px;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(self.status_label)

        # Botão de controle
        self.control_button = QPushButton("▶️ Iniciar")
        self.control_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.control_button.clicked.connect(self._toggle_monitoring)
        header_layout.addWidget(self.control_button)

        layout.addWidget(header_frame)

    def _create_metrics_panel(self, splitter: QSplitter):
        """Cria painel de métricas."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(16)

        # Título
        title_label = QLabel("📈 Métricas em Tempo Real")
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)

        # Grid de métricas
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        # Criar cards de métricas
        self.metric_cards["cpu"] = MetricCard("CPU", "🔧", "%")
        self.metric_cards["memory"] = MetricCard("Memória", "💾", "%")
        self.metric_cards["disk"] = MetricCard("Disco", "💿", "%")
        self.metric_cards["network"] = MetricCard("Rede", "🌐", " MB/s")

        # Adicionar ao grid
        metrics_grid.addWidget(self.metric_cards["cpu"], 0, 0)
        metrics_grid.addWidget(self.metric_cards["memory"], 0, 1)
        metrics_grid.addWidget(self.metric_cards["disk"], 1, 0)
        metrics_grid.addWidget(self.metric_cards["network"], 1, 1)

        layout.addLayout(metrics_grid)
        
        splitter.addWidget(panel)

    def _create_details_panel(self, splitter: QSplitter):
        """Cria painel de detalhes."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        # Painel de processos
        processes_group = QGroupBox("🔄 Processos (Top 10)")
        processes_layout = QVBoxLayout(processes_group)
        
        self.process_table = ProcessTable()
        processes_layout.addWidget(self.process_table)
        
        layout.addWidget(processes_group, 2)

        # Painel de alertas
        self.alerts_panel = AlertsPanel()
        layout.addWidget(self.alerts_panel, 1)
        
        splitter.addWidget(panel)

    def _apply_modern_style(self):
        """Aplica estilo moderno ao widget."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                color: #495057;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                background-color: #f8f9fa;
            }
        """)

    def _toggle_monitoring(self):
        """Alterna monitoramento do sistema."""
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        """Inicia monitoramento do sistema."""
        if self.monitor_worker and self.monitor_worker.isRunning():
            return

        self.is_monitoring = True
        self.control_button.setText("⏸️ Parar")
        self.status_label.setText("▶️ Monitorando")
        
        # Iniciar worker
        self.monitor_worker = SystemMonitorWorker(self.container)
        self.monitor_worker.metrics_updated.connect(self._on_metrics_updated)
        self.monitor_worker.alert_generated.connect(self._on_alert_generated)
        self.monitor_worker.error_occurred.connect(self._on_monitoring_error)
        self.monitor_worker.start()

    def _stop_monitoring(self):
        """Para monitoramento do sistema."""
        self.is_monitoring = False
        self.control_button.setText("▶️ Iniciar")
        self.status_label.setText("⏸️ Parado")
        
        if self.monitor_worker:
            self.monitor_worker.stop()
            self.monitor_worker.quit()
            self.monitor_worker.wait()

    def _on_metrics_updated(self, metrics: SystemMetrics):
        """Manipula atualização de métricas."""
        # Atualizar cards de métricas
        self.metric_cards["cpu"].update_value(metrics.cpu_usage)
        self.metric_cards["memory"].update_value(metrics.memory_usage)
        self.metric_cards["disk"].update_value(metrics.disk_usage)
        self.metric_cards["network"].update_value(metrics.network_io_mbps)
        
        # Atualizar tabela de processos
        if hasattr(metrics, 'top_processes'):
            self.process_table.update_processes(metrics.top_processes)
        
        # Emitir sinal
        self.metrics_updated.emit(metrics)

    def _on_alert_generated(self, alert: SystemAlert):
        """Manipula geração de alerta."""
        self.alerts_panel.add_alert(alert)
        self.alert_generated.emit(alert)

    def _on_monitoring_error(self, error_message: str):
        """Manipula erro no monitoramento."""
        self.logger.error(f"Erro no monitoramento: {error_message}")
        self._stop_monitoring()

    def get_current_metrics(self) -> Dict[str, float]:
        """Retorna métricas atuais."""
        return {
            "cpu": self.metric_cards["cpu"].current_value,
            "memory": self.metric_cards["memory"].current_value,
            "disk": self.metric_cards["disk"].current_value,
            "network": self.metric_cards["network"].current_value
        }

    def closeEvent(self, event):
        """Manipula fechamento do widget."""
        self._stop_monitoring()
        super().closeEvent(event)