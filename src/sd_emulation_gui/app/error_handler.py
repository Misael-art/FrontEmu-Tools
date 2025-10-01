"""
Error Handler Module

This module provides centralized error handling and user feedback
for the SD Emulation GUI application.
"""

import logging
import sys
import traceback
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Error categories."""
    IMPORT_ERROR = "IMPORT_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    GUI_ERROR = "GUI_ERROR"
    FILE_SYSTEM_ERROR = "FILE_SYSTEM_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorHandler:
    """Centralized error handling system."""

    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger(__name__)
        self.error_history: list = []

    def handle_error(
        self,
        error: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[str] = None,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle an error and provide structured response."""
        # Create error record
        error_record = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": category.value,
            "severity": severity.value,
            "context": context,
            "traceback": traceback.format_exc(),
            "timestamp": self._get_timestamp(),
            "user_message": user_message or self._get_default_user_message(error, category)
        }

        # Log the error
        self._log_error(error_record, severity)

        # Store in history
        self.error_history.append(error_record)

        return error_record

    def _log_error(self, error_record: Dict[str, Any], severity: ErrorSeverity) -> None:
        """Log error with appropriate level."""
        message = f"[{error_record['category']}] {error_record['error_message']}"
        if error_record['context']:
            message = f"{message} (Context: {error_record['context']})"

        if severity == ErrorSeverity.DEBUG:
            self.logger.debug(message)
        elif severity == ErrorSeverity.INFO:
            self.logger.info(message)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(message)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(message)
        elif severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message)

    def _get_default_user_message(self, error: Exception, category: ErrorCategory) -> str:
        """Get default user-friendly message for error type."""
        messages = {
            ErrorCategory.IMPORT_ERROR: (
                "O sistema encontrou um problema ao carregar componentes necessários. "
                "Isso pode ser causado por arquivos ausentes ou configurações incorretas."
            ),
            ErrorCategory.CONFIGURATION_ERROR: (
                "Há um problema na configuração do sistema. "
                "Verifique se os arquivos de configuração estão corretos."
            ),
            ErrorCategory.VALIDATION_ERROR: (
                "Os dados fornecidos não passaram na validação. "
                "Verifique se as informações estão no formato correto."
            ),
            ErrorCategory.GUI_ERROR: (
                "Ocorreu um problema na interface gráfica. "
                "Tente reiniciar a aplicação."
            ),
            ErrorCategory.FILE_SYSTEM_ERROR: (
                "Não foi possível acessar arquivos ou diretórios. "
                "Verifique as permissões e se os caminhos existem."
            ),
            ErrorCategory.NETWORK_ERROR: (
                "Problema de conectividade. "
                "Verifique sua conexão com a internet."
            ),
            ErrorCategory.UNKNOWN_ERROR: (
                "Ocorreu um erro inesperado. "
                "Os detalhes foram registrados nos logs do sistema."
            )
        }

        return messages.get(category, messages[ErrorCategory.UNKNOWN_ERROR])

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error history."""
        if not self.error_history:
            return {"total_errors": 0, "by_category": {}, "by_severity": {}}

        by_category = {}
        by_severity = {}

        for error in self.error_history:
            category = error["category"]
            severity = error["severity"]

            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "by_category": by_category,
            "by_severity": by_severity,
            "latest_error": self.error_history[-1] if self.error_history else None
        }

    def clear_error_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()


# Global error handler instance
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _global_error_handler


def handle_exception(
    error: Exception,
    category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    context: Optional[str] = None,
    user_message: Optional[str] = None
) -> Dict[str, Any]:
    """Handle an exception with the global error handler."""
    return _global_error_handler.handle_error(error, category, severity, context, user_message)


def log_error(
    message: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    context: Optional[str] = None
) -> None:
    """Log an error message."""
    error_record = {
        "error_type": "CustomError",
        "error_message": message,
        "category": category.value,
        "severity": severity.value,
        "context": context,
        "traceback": "",
        "timestamp": _global_error_handler._get_timestamp(),
        "user_message": message
    }

    _global_error_handler._log_error(error_record, severity)
    _global_error_handler.error_history.append(error_record)


def get_error_summary() -> Dict[str, Any]:
    """Get error summary from global error handler."""
    return _global_error_handler.get_error_summary()


def clear_errors() -> None:
    """Clear error history from global error handler."""
    _global_error_handler.clear_error_history()


# Exception hook for unhandled exceptions
def setup_global_exception_handler():
    """Set up global exception handler for unhandled exceptions."""

    def exception_handler(exc_type, exc_value, exc_traceback):
        """Handle unhandled exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't handle KeyboardInterrupt (Ctrl+C)
            return

        error_message = f"Unhandled {exc_type.__name__}: {exc_value}"
        context = "Global exception handler"

        error_record = handle_exception(
            exc_value,
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )

        print(f"\n🚨 ERRO CRÍTICO NÃO TRATADO: {error_message}")
        print(f"📋 Detalhes: {error_record['user_message']}")
        print("📝 Verifique os logs para mais informações.")
        print("💡 Sugestão: Reinicie a aplicação.")

        # Don't exit, let the application continue if possible
        # sys.exit(1)

    # Set the exception handler
    sys.excepthook = exception_handler
