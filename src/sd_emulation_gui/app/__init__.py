"""
Application Layer

Camada de aplicação que coordena inicialização, container de dependências,
configuração de logging e ponto de entrada principal.
"""

from .main import main, setup_application
from .container import ApplicationContainer

__all__ = ["main", "setup_application", "ApplicationContainer"]