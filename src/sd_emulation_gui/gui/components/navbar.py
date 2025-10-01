"""Componente de navegação principal da aplicação."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)


class Navbar(QWidget):
    """Barra de navegação com botões para diferentes seções."""

    # Sinais para navegação
    dashboard_clicked = Signal()
    validation_clicked = Signal()
    migration_clicked = Signal()
    coverage_clicked = Signal()
    compliance_clicked = Signal()

    def __init__(self, parent=None):
        """Inicializa a barra de navegação."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Configura a interface da barra de navegação."""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        # Botões de navegação
        self.dashboard_btn = QPushButton("Dashboard")
        self.validation_btn = QPushButton("Validação")
        self.migration_btn = QPushButton("Migração")
        self.coverage_btn = QPushButton("Cobertura")
        self.compliance_btn = QPushButton("Compliance")

        # Conectar sinais
        self.dashboard_btn.clicked.connect(self.dashboard_clicked.emit)
        self.validation_btn.clicked.connect(self.validation_clicked.emit)
        self.migration_btn.clicked.connect(self.migration_clicked.emit)
        self.coverage_btn.clicked.connect(self.coverage_clicked.emit)
        self.compliance_btn.clicked.connect(self.compliance_clicked.emit)

        # Adicionar botões ao layout
        layout.addWidget(self.dashboard_btn)
        layout.addWidget(self.validation_btn)
        layout.addWidget(self.migration_btn)
        layout.addWidget(self.coverage_btn)
        layout.addWidget(self.compliance_btn)
        layout.addStretch()  # Espaço flexível à direita

        self.setLayout(layout)

    def set_active_button(self, button_name: str):
        """Define qual botão está ativo (destacado).
        
        Args:
            button_name: Nome do botão a ser destacado ('dashboard', 'validation', etc.)
        """
        # Reset all buttons
        buttons = [
            self.dashboard_btn,
            self.validation_btn,
            self.migration_btn,
            self.coverage_btn,
            self.compliance_btn,
        ]
        
        for btn in buttons:
            btn.setStyleSheet("")
        
        # Highlight active button
        active_style = "background-color: #0078d4; color: white; font-weight: bold;"
        
        if button_name == "dashboard":
            self.dashboard_btn.setStyleSheet(active_style)
        elif button_name == "validation":
            self.validation_btn.setStyleSheet(active_style)
        elif button_name == "migration":
            self.migration_btn.setStyleSheet(active_style)
        elif button_name == "coverage":
            self.coverage_btn.setStyleSheet(active_style)
        elif button_name == "compliance":
            self.compliance_btn.setStyleSheet(active_style)