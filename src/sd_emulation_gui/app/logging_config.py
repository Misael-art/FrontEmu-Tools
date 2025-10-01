"""
Logging Configuration

This module provides structured logging configuration with rotation,
correlation IDs, and configurable levels for the SD Emulation GUI application.
"""

import logging
import logging.handlers
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import colorlog

# Context variable for correlation ID
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class UTF8SafeFileHandler(logging.handlers.RotatingFileHandler):
    """Custom file handler with enhanced UTF-8 support and error handling."""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding='utf-8', delay=False, errors='replace'):
        """Initialize UTF-8 safe file handler with error handling."""
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay, errors)
    
    def emit(self, record):
        """Emit a record with UTF-8 safe handling."""
        try:
            # Ensure message is UTF-8 safe
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                # Replace problematic characters that might cause encoding issues
                record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8')
            super().emit(record)
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            # Fallback: create a safe version of the record
            safe_record = logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=f"[UTF-8 Error] Original message contained invalid characters: {str(e)}",
                args=(),
                exc_info=None
            )
            super().emit(safe_record)
        except Exception as e:
            # Last resort: log the error to stderr
            sys.stderr.write(f"Logging error: {e}\n")


class CorrelationIdFormatter(logging.Formatter):
    """Custom formatter that includes correlation IDs with UTF-8 safety."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with correlation ID and UTF-8 safety."""
        # Add correlation ID to the record
        cid = correlation_id.get()
        if cid:
            record.correlation_id = cid
        else:
            record.correlation_id = "none"
        
        try:
            formatted = super().format(record)
            # Ensure the formatted message is UTF-8 safe
            return formatted.encode('utf-8', errors='replace').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Fallback to a safe message
            return f"{record.asctime} [{record.levelname}] [{record.correlation_id}] {record.name}: [UTF-8 Error in message]"


class ColoredCorrelationFormatter(colorlog.ColoredFormatter):
    """Colored formatter that includes correlation IDs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with correlation ID and colors."""
        # Add correlation ID to the record
        cid = correlation_id.get()
        if cid:
            record.correlation_id = cid
        else:
            record.correlation_id = "none"

        return super().format(record)


class OperationContext:
    """Context manager for operations with correlation IDs."""

    def __init__(self, operation_name: str, logger: logging.Logger | None = None):
        """
        Initialize operation context.

        Args:
            operation_name: Name of the operation
            logger: Logger instance to use
        """
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.correlation_id = str(uuid4())[:8]
        self.start_time = None
        self._token = None

    def __enter__(self) -> str:
        """Enter operation context."""
        self.start_time = datetime.now()
        self._token = correlation_id.set(self.correlation_id)

        self.logger.info(
            f"Operation started: {self.operation_name}",
            extra={"operation": self.operation_name},
        )
        return self.correlation_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit operation context."""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(
                f"Operation completed: {self.operation_name} (duration: {duration:.2f}s)",
                extra={"operation": self.operation_name, "duration": duration},
            )
        else:
            self.logger.error(
                f"Operation failed: {self.operation_name} (duration: {duration:.2f}s) - {exc_val}",
                extra={
                    "operation": self.operation_name,
                    "duration": duration,
                    "error": str(exc_val),
                },
            )

        if self._token:
            correlation_id.reset(self._token)


class LoggingConfig:
    """Centralized logging configuration."""

    def __init__(self, base_dir: str = "logs"):
        """
        Initialize logging configuration.

        Args:
            base_dir: Base directory for log files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        self._loggers_configured = set()

    def setup_logging(
        self,
        level: str = "INFO",
        console_output: bool = True,
        file_output: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 10,
        correlation_ids: bool = True,
    ) -> None:
        """
        Set up application logging configuration.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to output to console
            file_output: Whether to output to file
            max_file_size: Maximum size per log file in bytes
            backup_count: Number of backup files to keep
            correlation_ids: Whether to include correlation IDs
        """
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set root level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)

        # Format strings
        if correlation_ids:
            console_format = (
                "%(log_color)s%(asctime)s [%(levelname)8s] "
                "[%(correlation_id)s] %(name)s: %(message)s%(reset)s"
            )
            file_format = (
                "%(asctime)s [%(levelname)8s] [%(correlation_id)s] "
                "%(name)s:%(lineno)d - %(message)s"
            )
        else:
            console_format = (
                "%(log_color)s%(asctime)s [%(levelname)8s] "
                "%(name)s: %(message)s%(reset)s"
            )
            file_format = (
                "%(asctime)s [%(levelname)8s] " "%(name)s:%(lineno)d - %(message)s"
            )

        # Console handler with colors
        if console_output:
            console_handler = colorlog.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)

            if correlation_ids:
                console_formatter = ColoredCorrelationFormatter(
                    console_format,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red,bg_white",
                    },
                )
            else:
                console_formatter = colorlog.ColoredFormatter(
                    console_format,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red,bg_white",
                    },
                )

            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # File handler with rotation and UTF-8 safety
        if file_output:
            log_file = self.base_dir / "sd_emulation_gui.log"
            file_handler = UTF8SafeFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding="utf-8",
                errors="replace"
            )
            file_handler.setLevel(numeric_level)

            file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")

            if correlation_ids:
                # Wrap with correlation ID formatter
                file_formatter = self._wrap_with_correlation(file_formatter)

            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        # Configure specific loggers
        self._configure_component_loggers(numeric_level)

        # Log configuration completion
        logger = logging.getLogger(__name__)
        logger.info(
            f"Logging configured - Level: {level}, Console: {console_output}, "
            f"File: {file_output}, Correlation IDs: {correlation_ids}"
        )

    def _wrap_with_correlation(
        self, formatter: logging.Formatter
    ) -> CorrelationIdFormatter:
        """Wrap formatter with correlation ID support."""
        correlation_formatter = CorrelationIdFormatter()
        correlation_formatter._style = formatter._style
        correlation_formatter._fmt = formatter._fmt
        correlation_formatter.datefmt = formatter.datefmt
        return correlation_formatter

    def _configure_component_loggers(self, level: int) -> None:
        """Configure loggers for specific components."""
        component_configs = {
            "domain": level,
            "services": level,
            "adapters": level,
            "gui": level,
            "app": level,
            # Third-party libraries
            "PySide6": logging.WARNING,
            "urllib3": logging.WARNING,
            "requests": logging.WARNING,
        }

        for component, component_level in component_configs.items():
            logger = logging.getLogger(component)
            logger.setLevel(component_level)
            self._loggers_configured.add(component)

    def create_component_logger(
        self, component_name: str, log_file: str | None = None, level: str | None = None
    ) -> logging.Logger:
        """
        Create a component-specific logger.

        Args:
            component_name: Name of the component
            log_file: Optional separate log file for this component
            level: Optional specific level for this component

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(component_name)

        if component_name in self._loggers_configured:
            return logger

        # Set level if specified
        if level:
            numeric_level = getattr(logging, level.upper(), logging.INFO)
            logger.setLevel(numeric_level)

        # Add separate file handler if requested
        if log_file:
            file_path = self.base_dir / log_file
            file_handler = UTF8SafeFileHandler(
                file_path,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5,
                encoding="utf-8",
                errors="replace"
            )

            file_formatter = CorrelationIdFormatter(
                "%(asctime)s [%(levelname)8s] [%(correlation_id)s] "
                "%(name)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        self._loggers_configured.add(component_name)
        return logger

    def get_log_stats(self) -> dict[str, Any]:
        """Get logging statistics."""
        stats = {
            "configured_loggers": len(self._loggers_configured),
            "logger_names": list(self._loggers_configured),
            "log_directory": str(self.base_dir.absolute()),
            "log_files": [],
        }

        # Get log file information
        try:
            for log_file in self.base_dir.glob("*.log*"):
                file_stat = log_file.stat()
                stats["log_files"].append(
                    {
                        "name": log_file.name,
                        "size_bytes": file_stat.st_size,
                        "size_mb": file_stat.st_size / (1024 * 1024),
                        "modified": datetime.fromtimestamp(
                            file_stat.st_mtime
                        ).isoformat(),
                    }
                )
        except Exception as e:
            stats["log_files_error"] = str(e)

        return stats

    def cleanup_old_logs(self, max_age_days: int = 30) -> int:
        """
        Clean up old log files.

        Args:
            max_age_days: Maximum age in days for log files

        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

        try:
            for log_file in self.base_dir.glob("*.log.*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to clean up old logs: {e}")

        return cleaned_count


# Global logging configuration instance
_logging_config = LoggingConfig()


def setup_logging(
    level: str = "INFO",
    console_output: bool = True,
    file_output: bool = True,
    correlation_ids: bool = True,
) -> None:
    """Set up application logging (convenience function)."""
    _logging_config.setup_logging(
        level=level,
        console_output=console_output,
        file_output=file_output,
        correlation_ids=correlation_ids,
    )


def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """Get a configured logger (convenience function)."""
    return _logging_config.create_component_logger(name, log_file=log_file)


def operation_context(
    operation_name: str, logger: logging.Logger | None = None
) -> OperationContext:
    """Create an operation context (convenience function)."""
    return OperationContext(operation_name, logger)


def get_log_stats() -> dict[str, Any]:
    """Get logging statistics (convenience function)."""
    return _logging_config.get_log_stats()


def cleanup_old_logs(max_age_days: int = 30) -> int:
    """Clean up old log files (convenience function)."""
    return _logging_config.cleanup_old_logs(max_age_days)
