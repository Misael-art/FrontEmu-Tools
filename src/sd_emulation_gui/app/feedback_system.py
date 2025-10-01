"""
Feedback System Module

This module provides user feedback mechanisms for operations,
progress tracking, and status updates in the SD Emulation GUI.
"""

import time
from enum import Enum
from typing import Callable, Dict, List, Optional


class FeedbackLevel(Enum):
    """Feedback level for user messages."""
    SUCCESS = "SUCCESS"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    PROGRESS = "PROGRESS"


class FeedbackSystem:
    """Centralized feedback system for user interactions."""

    def __init__(self):
        """Initialize feedback system."""
        self._listeners: List[Callable] = []
        self._progress_callbacks: List[Callable] = []

    def add_listener(self, callback: Callable[[str, FeedbackLevel], None]) -> None:
        """Add a feedback listener."""
        self._listeners.append(callback)

    def add_progress_listener(self, callback: Callable[[str, int], None]) -> None:
        """Add a progress listener."""
        self._progress_callbacks.append(callback)

    def notify(self, message: str, level: FeedbackLevel = FeedbackLevel.INFO) -> None:
        """Notify all listeners with a message."""
        for listener in self._listeners:
            try:
                listener(message, level)
            except Exception:
                # Don't let listener errors break the system
                pass

    def notify_progress(self, message: str, progress: int) -> None:
        """Notify progress listeners."""
        for callback in self._progress_callbacks:
            try:
                callback(message, progress)
            except Exception:
                # Don't let callback errors break the system
                pass

    def success(self, message: str) -> None:
        """Show success message."""
        self.notify(f"✅ {message}", FeedbackLevel.SUCCESS)

    def info(self, message: str) -> None:
        """Show info message."""
        self.notify(f"ℹ️ {message}", FeedbackLevel.INFO)

    def warning(self, message: str) -> None:
        """Show warning message."""
        self.notify(f"⚠️ {message}", FeedbackLevel.WARNING)

    def error(self, message: str) -> None:
        """Show error message."""
        self.notify(f"❌ {message}", FeedbackLevel.ERROR)

    def progress(self, message: str, percent: int = 0) -> None:
        """Show progress message."""
        self.notify(f"🔄 {message}", FeedbackLevel.PROGRESS)
        if percent > 0:
            self.notify_progress(message, percent)


class ProgressTracker:
    """Track progress of long-running operations."""

    def __init__(self, feedback_system: FeedbackSystem):
        """Initialize progress tracker."""
        self.feedback_system = feedback_system
        self._current_operation: Optional[str] = None
        self._start_time: Optional[float] = None
        self._steps_completed = 0
        self._total_steps = 0

    def start_operation(self, operation_name: str, total_steps: int = 1) -> None:
        """Start tracking an operation."""
        self._current_operation = operation_name
        self._start_time = time.time()
        self._steps_completed = 0
        self._total_steps = total_steps

        self.feedback_system.progress(f"Iniciando: {operation_name}", 0)

    def update_progress(self, step_description: str = "") -> None:
        """Update progress for current operation."""
        if not self._current_operation:
            return

        self._steps_completed += 1
        progress_percent = min(100, int((self._steps_completed / self._total_steps) * 100))

        message = f"{self._current_operation}"
        if step_description:
            message += f" - {step_description}"

        self.feedback_system.progress(message, progress_percent)

    def complete_operation(self, success_message: Optional[str] = None) -> None:
        """Complete the current operation."""
        if not self._current_operation:
            return

        elapsed_time = time.time() - self._start_time if self._start_time else 0
        message = success_message or f"Operação concluída: {self._current_operation}"

        if elapsed_time > 0:
            message += f" (tempo: {elapsed_time:.2f}s)".2f"
        self.feedback_system.success(message)

        self._current_operation = None
        self._start_time = None


class StatusManager:
    """Manage application status and user feedback."""

    def __init__(self, feedback_system: FeedbackSystem):
        """Initialize status manager."""
        self.feedback_system = feedback_system
        self._current_status = "Pronto"
        self._is_busy = False

    def set_status(self, status: str) -> None:
        """Set current application status."""
        self._current_status = status
        self.feedback_system.info(f"Status: {status}")

    def set_busy(self, is_busy: bool, operation: str = "") -> None:
        """Set busy state."""
        self._is_busy = is_busy
        if is_busy:
            self.feedback_system.progress(f"Executando: {operation}")
        else:
            self.feedback_system.info("Operação concluída")

    def show_message(self, title: str, message: str, level: FeedbackLevel = FeedbackLevel.INFO) -> None:
        """Show a message to the user."""
        formatted_message = f"{title}: {message}"
        self.feedback_system.notify(formatted_message, level)

    def show_error_dialog(self, title: str, message: str, details: Optional[str] = None) -> None:
        """Show error dialog information."""
        error_info = f"{title}: {message}"
        if details:
            error_info += f"\nDetalhes: {details}"

        self.feedback_system.error(error_info)

    def show_success_dialog(self, title: str, message: str) -> None:
        """Show success dialog information."""
        success_info = f"{title}: {message}"
        self.feedback_system.success(success_info)


# Global instances
_global_feedback_system = FeedbackSystem()
_global_progress_tracker = ProgressTracker(_global_feedback_system)
_global_status_manager = StatusManager(_global_feedback_system)


def get_feedback_system() -> FeedbackSystem:
    """Get the global feedback system."""
    return _global_feedback_system


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker."""
    return _global_progress_tracker


def get_status_manager() -> StatusManager:
    """Get the global status manager."""
    return _global_status_manager


def show_message(message: str, level: FeedbackLevel = FeedbackLevel.INFO) -> None:
    """Show a message using the global feedback system."""
    _global_feedback_system.notify(message, level)


def show_progress(message: str, percent: int = 0) -> None:
    """Show progress using the global feedback system."""
    _global_feedback_system.progress(message, percent)


def show_success(message: str) -> None:
    """Show success message."""
    _global_feedback_system.success(message)


def show_error(message: str) -> None:
    """Show error message."""
    _global_feedback_system.error(message)


def show_warning(message: str) -> None:
    """Show warning message."""
    _global_feedback_system.warning(message)


def show_info(message: str) -> None:
    """Show info message."""
    _global_feedback_system.info(message)
