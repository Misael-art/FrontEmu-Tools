"""Componente de carregamento para operações assíncronas."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class LoaderWidget(QWidget):
    """Widget de carregamento com barra de progresso e mensagem."""

    def __init__(self, parent=None):
        """Inicializa o widget de carregamento."""
        super().__init__(parent)
        self._setup_ui()
        self.hide()  # Inicialmente oculto

    def _setup_ui(self):
        """Configura a interface do widget de carregamento."""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Label de status
        self.status_label = QLabel("Carregando...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Progresso indeterminado
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def show_loading(self, message: str = "Carregando..."):
        """Mostra o widget de carregamento com uma mensagem.
        
        Args:
            message: Mensagem a ser exibida durante o carregamento
        """
        self.status_label.setText(message)
        self.show()

    def hide_loading(self):
        """Oculta o widget de carregamento."""
        self.hide()

    def update_message(self, message: str):
        """Atualiza a mensagem de carregamento.
        
        Args:
            message: Nova mensagem a ser exibida
        """
        self.status_label.setText(message)