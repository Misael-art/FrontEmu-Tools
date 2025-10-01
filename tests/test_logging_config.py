"""Tests for logging configuration module."""

import logging
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.logging_config import (
    LoggingConfig,
    UTF8SafeFileHandler,
    CorrelationIdFormatter,
    OperationContext,
    correlation_id,
    setup_logging,
    get_logger,
    operation_context,
)


class TestUTF8SafeFileHandler:
    """Test UTF-8 safe file handler."""

    def test_initialization(self):
        """Test handler initialization with UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = Path(tmp_dir) / 'test.log'
            handler = UTF8SafeFileHandler(
                str(tmp_file),
                encoding='utf-8',
                errors='replace'
            )
            assert handler.encoding == 'utf-8'
            assert handler.errors == 'replace'
            handler.close()

    def test_emit_with_utf8_message(self):
        """Test emitting log record with UTF-8 characters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = Path(tmp_dir) / 'test.log'
            handler = UTF8SafeFileHandler(
                str(tmp_file),
                encoding='utf-8',
                errors='replace'
            )
            
            # Create a log record with UTF-8 characters
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message with UTF-8: ñáéíóú 中文 🚀',
                args=(),
                exc_info=None
            )
            
            # Should not raise an exception
            handler.emit(record)
            handler.close()
            
            # Verify content was written
            with open(tmp_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'ñáéíóú' in content
                assert '中文' in content
                assert '🚀' in content

    def test_emit_with_invalid_encoding(self):
        """Test emitting log record with invalid encoding characters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = Path(tmp_dir) / 'test.log'
            handler = UTF8SafeFileHandler(
                str(tmp_file),
                encoding='utf-8',
                errors='replace'
            )
            
            # Create a record with problematic message
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None
            )
            
            # Simulate encoding error by patching
            with patch.object(handler, 'stream') as mock_stream:
                mock_stream.write.side_effect = UnicodeEncodeError(
                    'utf-8', 'test', 0, 1, 'invalid character'
                )
                
                # Should handle the error gracefully
                handler.emit(record)
            
            handler.close()


class TestCorrelationIdFormatter:
    """Test correlation ID formatter."""

    def test_format_with_correlation_id(self):
        """Test formatting with correlation ID."""
        formatter = CorrelationIdFormatter(
            '%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s'
        )
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        # Set correlation ID
        token = correlation_id.set('test-123')
        try:
            formatted = formatter.format(record)
            assert 'test-123' in formatted
            assert 'Test message' in formatted
        finally:
            correlation_id.reset(token)

    def test_format_without_correlation_id(self):
        """Test formatting without correlation ID."""
        formatter = CorrelationIdFormatter(
            '%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s'
        )
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert 'none' in formatted
        assert 'Test message' in formatted

    def test_format_with_utf8_characters(self):
        """Test formatting with UTF-8 characters."""
        formatter = CorrelationIdFormatter(
            '%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s'
        )
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Message with UTF-8: ñáéíóú 中文 🚀',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert 'ñáéíóú' in formatted
        assert '中文' in formatted
        assert '🚀' in formatted

    def test_format_with_encoding_error(self):
        """Test formatting with encoding error."""
        formatter = CorrelationIdFormatter(
            '%(levelname)s [%(correlation_id)s] %(name)s: %(message)s'
        )
        
        # Create a simple record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        # Add asctime attribute that the formatter expects
        record.asctime = '2023-01-01 12:00:00'
        
        # Test that the formatter handles encoding errors gracefully
        # by mocking the parent format method to raise UnicodeEncodeError
        def mock_format_error(self, record):
            raise UnicodeEncodeError('utf-8', 'test', 0, 1, 'invalid character')
        
        with patch.object(logging.Formatter, 'format', mock_format_error):
            formatted = formatter.format(record)
            assert '[UTF-8 Error in message]' in formatted


class TestOperationContext:
    """Test operation context manager."""

    def test_successful_operation(self, caplog):
        """Test successful operation context."""
        logger = logging.getLogger('test')
        logger.setLevel(logging.INFO)
        
        with caplog.at_level(logging.INFO):
            with operation_context('test_operation', logger) as cid:
                assert cid is not None
                assert len(cid) == 8  # UUID first 8 characters
                
                # Verify correlation ID is set
                assert correlation_id.get() == cid
        
        # Check logs
        assert 'Operation started: test_operation' in caplog.text
        assert 'Operation completed: test_operation' in caplog.text

    def test_failed_operation(self, caplog):
        """Test failed operation context."""
        logger = logging.getLogger('test')
        logger.setLevel(logging.INFO)
        
        with caplog.at_level(logging.INFO):
            with pytest.raises(ValueError):
                with operation_context('test_operation', logger):
                    raise ValueError('Test error')
        
        # Check logs
        assert 'Operation started: test_operation' in caplog.text
        assert 'Operation failed: test_operation' in caplog.text
        assert 'Test error' in caplog.text

    def test_correlation_id_cleanup(self):
        """Test correlation ID is cleaned up after context."""
        logger = logging.getLogger('test')
        
        # Ensure no correlation ID initially
        assert correlation_id.get() is None
        
        with operation_context('test_operation', logger):
            assert correlation_id.get() is not None
        
        # Should be cleaned up
        assert correlation_id.get() is None


class TestLoggingConfig:
    """Test logging configuration class."""

    def test_initialization(self):
        """Test logging config initialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = LoggingConfig(base_dir=tmp_dir)
            assert config.base_dir == Path(tmp_dir)
            assert config.base_dir.exists()
            assert len(config._loggers_configured) == 0

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Ensure the directory exists and is valid
            logs_dir = os.path.join(tmp_dir, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            config = LoggingConfig(base_dir=logs_dir)
            
            # Clear existing handlers first
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            config.setup_logging(
                level='INFO',
                console_output=True,
                file_output=False,  # Disable file output to avoid directory issues
                correlation_ids=True
            )
            
            # Check root logger configuration
            assert root_logger.level == logging.INFO
            assert len(root_logger.handlers) >= 1

    def test_create_component_logger(self):
        """Test creating component-specific logger."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Ensure the directory exists and is valid
            logs_dir = os.path.join(tmp_dir, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            config = LoggingConfig(base_dir=logs_dir)
            
            logger = config.create_component_logger(
                'test_component_unique',
                log_file=None,  # Disable file output to avoid directory issues
                level='DEBUG'
            )
            
            assert logger.name == 'test_component_unique'
            assert logger.level == logging.DEBUG
            assert 'test_component_unique' in config._loggers_configured

    def test_get_log_stats(self):
        """Test getting log statistics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = LoggingConfig(base_dir=tmp_dir)
            
            # Create a test log file
            test_log = Path(tmp_dir) / 'test.log'
            test_log.write_text('test log content')
            
            stats = config.get_log_stats()
            
            assert 'configured_loggers' in stats
            assert 'logger_names' in stats
            assert 'log_directory' in stats
            assert 'log_files' in stats
            assert len(stats['log_files']) >= 1

    def test_cleanup_old_logs(self):
        """Test cleaning up old log files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = LoggingConfig(base_dir=tmp_dir)
            
            # Create test log files
            old_log = Path(tmp_dir) / 'old.log.1'
            new_log = Path(tmp_dir) / 'new.log.1'
            
            old_log.write_text('old log')
            new_log.write_text('new log')
            
            # Mock file modification times
            import os
            import time
            
            # Set old file to 40 days ago
            old_time = time.time() - (40 * 24 * 60 * 60)
            os.utime(old_log, (old_time, old_time))
            
            # Clean up files older than 30 days
            cleaned = config.cleanup_old_logs(max_age_days=30)
            
            assert cleaned >= 1
            assert not old_log.exists()
            assert new_log.exists()


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_setup_logging_function(self):
        """Test setup_logging convenience function."""
        # Should not raise an exception
        setup_logging(
            level='INFO',
            console_output=True,
            file_output=False,  # Avoid file creation in tests
            correlation_ids=True
        )
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_get_logger_function(self):
        """Test get_logger convenience function."""
        logger = get_logger('test_logger')
        assert logger.name == 'test_logger'
        assert isinstance(logger, logging.Logger)

    def test_operation_context_function(self):
        """Test operation_context convenience function."""
        context = operation_context('test_op')
        assert isinstance(context, OperationContext)
        assert context.operation_name == 'test_op'