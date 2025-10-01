"""Tests for BaseService module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from utils.base_service import BaseService
from meta.config.path_config import PathConfigManager


class TestService(BaseService):
    """Concrete implementation of BaseService for testing."""

    def initialize(self):
        self.initialized_flag = True

class TestBaseService:
    """Test cases for BaseService class."""
    
    @pytest.fixture
    def mock_path_config(self):
        """Mock PathConfigManager."""
        with patch('meta.config.path_config.PathConfigManager') as mock:
            yield mock
    
    def test_service_initialization_success(self, mock_path_config):
        """Test successful service initialization."""
        service = TestService()
        assert service.is_initialized() == True
        assert service.base_path is not None
        assert service.config_path is not None
        
    def test_service_initialization_failure(self, mock_path_config):
        """Test service initialization failure."""
        class FailingService(BaseService):
            def initialize(self):
                raise Exception("Init failed")
        
        with pytest.raises(Exception, match="Init failed"):
            FailingService()
    
    def test_service_with_custom_paths(self, mock_path_config):
        """Test service initialization with custom paths."""
        custom_base = Path("/custom/base")
        custom_config = Path("/custom/config")
        
        service = TestService(
            base_path=custom_base,
            config_path=custom_config
        )
        
        assert service.base_path == custom_base
        assert service.config_path == custom_config
        
    def test_validate_path_exists_true(self, mock_path_config, tmp_path):
        """Test path validation for existing path."""
        service = TestService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        assert service.validate_path_exists(test_file) == True
        
    def test_validate_path_exists_false(self, mock_path_config, tmp_path):
        """Test path validation for non-existing path."""
        service = TestService()
        non_existing = tmp_path / "non_existing.txt"
        
        assert service.validate_path_exists(non_existing) == False
        
    def test_validate_path_create_missing_file(self, mock_path_config, tmp_path):
        """Test path validation with file creation."""
        service = TestService()
        missing_file = tmp_path / "missing" / "file.txt"
        
        assert service.validate_path_exists(missing_file, create_if_missing=True) == True
        assert missing_file.parent.exists() == True
        
    def test_validate_path_create_missing_directory(self, mock_path_config, tmp_path):
        """Test path validation with directory creation."""
        service = TestService()
        missing_dir = tmp_path / "missing" / "directory"
        
        assert service.validate_path_exists(missing_dir, create_if_missing=True) == True
        assert missing_dir.exists() == True
        
    def test_config_cache_operations(self, mock_path_config):
        """Test configuration caching operations."""
        service = TestService()
        
        # Test caching
        service.cache_config("test_key", "test_value")
        assert service.get_cached_config("test_key") == "test_value"
        
        # Test default value
        assert service.get_cached_config("missing_key", "default") == "default"
        
        # Test cache clearing
        service.clear_cache()
        assert service.get_cached_config("test_key") is None
        
    def test_get_service_info(self, mock_path_config):
        """Test service information retrieval."""
        service = TestService()
        info = service.get_service_info()
        
        assert "class_name" in info
        assert "initialized" in info
        assert "base_path" in info
        assert "config_path" in info
        assert "cache_size" in info
        assert "logger_name" in info
        
    def test_recursion_protection(self, mock_path_config):
        """Test recursion protection in initialization."""
        class RecursiveService(BaseService):
            def initialize(self):
                pass
            
            def __init__(self, *args, **kwargs):
                kwargs['depth'] = 15  # Force recursion error
                super().__init__(*args, **kwargs)
        
        with pytest.raises(RecursionError, match="Max recursion depth exceeded"):
            RecursiveService()
                
    def test_get_resolved_path_without_resolver(self, mock_path_config):
        """Test path resolution without path resolver."""
        service = TestService()
        service.path_resolver = None
        
        resolved = service.get_resolved_path("test_path", "subpath")
        expected = Path("test_path") / "subpath"
        
        assert resolved == expected