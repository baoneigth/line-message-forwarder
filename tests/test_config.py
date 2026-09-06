"""
Tests for config module
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestConfig:
    """Test configuration loading"""
    
    @patch.dict(os.environ, {
        'LINE_EMAIL': 'test@example.com',
        'LINE_PASSWORD': 'password123',
        'FORWARD_MODE': 'on',
        'TARGET_GROUP_ID': 'C123456789',
        'TARGET_USER_ID': 'U123456789'
    })
    def test_config_loading(self):
        """Test that config loads environment variables correctly"""
        # Reload config module to pick up new env vars
        import importlib
        import config
        importlib.reload(config)
        
        assert config.LINE_EMAIL == 'test@example.com'
        assert config.LINE_PASSWORD == 'password123'
        assert config.FORWARD_MODE is True
        assert config.TARGET_GROUP_ID == 'C123456789'
        assert config.TARGET_USER_ID == 'U123456789'
    
    def test_forward_settings_structure(self):
        """Test that FORWARD_SETTINGS has expected structure"""
        import config
        
        expected_keys = {'text', 'image', 'sticker', 'video', 'audio'}
        assert set(config.FORWARD_SETTINGS.keys()) == expected_keys
        
        # All values should be boolean
        for value in config.FORWARD_SETTINGS.values():
            assert isinstance(value, bool)
    
    def test_commands_are_defined(self):
        """Test that all commands are defined"""
        import config
        
        assert hasattr(config, 'FORWARD_COMMAND')
        assert hasattr(config, 'STOP_COMMAND')
        assert hasattr(config, 'STATUS_COMMAND')
        assert hasattr(config, 'SET_TARGET_COMMAND')
        
        # Commands should start with '/'
        assert config.FORWARD_COMMAND.startswith('/')
        assert config.STOP_COMMAND.startswith('/')
        assert config.STATUS_COMMAND.startswith('/')
        assert config.SET_TARGET_COMMAND.startswith('/')
