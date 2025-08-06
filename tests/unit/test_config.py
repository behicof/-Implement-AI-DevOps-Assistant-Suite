"""
Unit tests for configuration manager
"""

import pytest
import tempfile
from pathlib import Path

from ai_devops.config.manager import ConfigManager


class TestConfigManager:
    """Test configuration management functionality"""
    
    def test_config_initialization(self):
        """Test config manager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            manager = ConfigManager(config_path=str(config_path))
            
            assert manager.config_file == config_path
            assert manager._config_cache is not None
    
    def test_default_config_structure(self):
        """Test default configuration structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            manager = ConfigManager(config_path=str(config_path))
            
            config = manager.get_config()
            
            # Check required sections exist
            assert "version" in config
            assert "general" in config
            assert "github" in config
            assert "exchanges" in config
            assert "ai" in config
            assert "monitor" in config
            assert "dashboard" in config
    
    def test_exchange_config(self):
        """Test exchange configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            manager = ConfigManager(config_path=str(config_path))
            
            exchange_config = manager.get_exchange_config()
            
            assert "supported" in exchange_config
            assert "binance" in exchange_config["supported"]
            assert "wallex" in exchange_config["supported"]
            assert "bitpin" in exchange_config["supported"]
            assert "nobitex" in exchange_config["supported"]
    
    def test_set_and_get_config(self):
        """Test setting and getting configuration values"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            manager = ConfigManager(config_path=str(config_path))
            
            # Set a test value
            manager.set_config("test_section", "test_key", "test_value")
            
            # Get the value back
            config = manager.get_config("test_section")
            assert config["test_key"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_validation(self):
        """Test configuration validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            manager = ConfigManager(config_path=str(config_path))
            
            validation = manager.validate_config()
            
            # Should have validation results for key sections
            assert "github" in validation
            assert "exchanges" in validation
            assert "ai" in validation
            assert "config_file" in validation