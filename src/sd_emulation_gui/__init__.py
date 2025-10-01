"""
SD Emulation GUI - Main Package

Este é o pacote principal da aplicação SD Emulation GUI.
Contém todos os módulos e componentes necessários para o funcionamento
da aplicação de gerenciamento de emulação SD.

Estrutura:
- app/: Camada de aplicação (main, container, logging)
- domain/: Camada de domínio (models, rules, types)
- services/: Camada de serviços (business logic)
- gui/: Interface gráfica (widgets, views, viewmodels)
- adapters/: Adaptadores de infraestrutura
- interfaces/: Contratos/interfaces
- utils/: Utilitários e serviços base
- validation/: Motor de validação
"""

__version__ = "0.1.0"
__author__ = "SD Emulation Team"

# Importações principais para facilitar o acesso
from .app.main import main
from .app.container import ApplicationContainer

__all__ = ["main", "ApplicationContainer"]
