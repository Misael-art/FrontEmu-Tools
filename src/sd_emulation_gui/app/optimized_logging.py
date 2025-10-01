"""
Optimized Logging Module

This module provides performance-optimized logging utilities
with async logging and smart buffering.
"""

import asyncio
import logging
import threading
from typing import Any, Dict, List, Optional
from queue import Queue
from datetime import datetime
import json


class AsyncLogHandler(logging.Handler):
    """Asynchronous log handler that doesn't block the main thread."""

    def __init__(self, max_queue_size: int = 1000):
        """Initialize async log handler."""
        super().__init__()
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._actual_handler = logging.StreamHandler()

        # Start worker thread
        self._start_worker()

    def _start_worker(self) -> None:
        """Start the background worker thread."""
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _process_queue(self) -> None:
        """Process log messages from queue."""
        while not self._stop_event.is_set():
            try:
                # Get log record with timeout
                record = self._queue.get(timeout=1.0)
                if record is None:
                    continue

                # Format and emit the record
                formatted_message = self.format(record)
                self._actual_handler.emit(record)

            except Exception:
                # Don't let logging errors break the system
                pass

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the queue."""
        try:
            # Put record in queue without blocking
            self._queue.put_nowait(record)
        except Exception:
            # Queue is full, drop the message
            pass

    def close(self) -> None:
        """Close the handler."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        self._actual_handler.close()
        super().close()


class BufferedLogHandler(logging.Handler):
    """Buffered log handler for batch processing."""

    def __init__(self, buffer_size: int = 50, flush_interval: float = 5.0):
        """Initialize buffered log handler."""
        super().__init__()
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self._buffer: List[logging.LogRecord] = []
        self._last_flush = time.time()
        self._lock = threading.RLock()
        self._actual_handler = logging.StreamHandler()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to buffer."""
        with self._lock:
            self._buffer.append(record)

            # Flush if buffer is full or time exceeded
            now = time.time()
            should_flush = (
                len(self._buffer) >= self.buffer_size or
                now - self._last_flush >= self.flush_interval
            )

            if should_flush:
                self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Flush all buffered records."""
        if not self._buffer:
            return

        # Process all buffered records
        for record in self._buffer:
            self._actual_handler.emit(record)

        self._buffer.clear()
        self._last_flush = time.time()

    def close(self) -> None:
        """Close the handler and flush remaining records."""
        with self._lock:
            self._flush_buffer()
        self._actual_handler.close()
        super().close()


class SmartFormatter(logging.Formatter):
    """Smart log formatter with performance optimizations."""

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """Initialize smart formatter."""
        super().__init__(fmt, datefmt)
        self._cache: Dict[str, str] = {}
        self._cache_lock = threading.RLock()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with caching."""
        # Create cache key
        cache_key = f"{record.levelname}:{record.getMessage()}"

        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

            # Format the record
            formatted = super().format(record)
            self._cache[cache_key] = formatted
            return formatted


class PerformanceLogger:
    """Performance-aware logger with optimizations."""

    def __init__(self, name: str, level: int = logging.INFO):
        """Initialize performance logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Add optimized handlers if not already present
        if not self.logger.handlers:
            # Add async handler for non-blocking logging
            async_handler = AsyncLogHandler()
            formatter = SmartFormatter(
                '%(asctime)s [%(levelname)8s] [%(correlation_id)s] %(name)s: %(message)s'
            )
            async_handler.setFormatter(formatter)
            self.logger.addHandler(async_handler)

        self._correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for logging."""
        self._correlation_id = correlation_id

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def _log(self, level: int, message: str, *args, **kwargs) -> None:
        """Internal logging method."""
        # Add correlation ID to record
        if self._correlation_id:
            kwargs['extra'] = kwargs.get('extra', {})
            kwargs['extra']['correlation_id'] = self._correlation_id

        self.logger.log(level, message, *args, **kwargs)

    def with_correlation(self, correlation_id: str) -> 'PerformanceLogger':
        """Create a logger instance with specific correlation ID."""
        new_logger = PerformanceLogger(self.logger.name, self.logger.level)
        new_logger.set_correlation_id(correlation_id)
        return new_logger


# Global performance logger factory
_logger_cache: Dict[str, PerformanceLogger] = {}
_logger_cache_lock = threading.RLock()


def get_performance_logger(name: str) -> PerformanceLogger:
    """Get or create a performance logger."""
    with _logger_cache_lock:
        if name not in _logger_cache:
            _logger_cache[name] = PerformanceLogger(name)
        return _logger_cache[name]


def configure_optimized_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    use_async: bool = True,
    buffer_size: int = 50
) -> None:
    """Configure optimized logging for the application."""
    if format_string is None:
        format_string = (
            '%(asctime)s [%(levelname)8s] [%(correlation_id)s] %(name)s: %(message)s'
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if use_async:
        # Use async handler for better performance
        handler = AsyncLogHandler()
    else:
        # Use buffered handler
        handler = BufferedLogHandler(buffer_size=buffer_size)

    formatter = SmartFormatter(format_string)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set up console handler for critical messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)  # Only show errors on console
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    print("✅ Optimized logging configured")
