"""
Tests for LineMessageForwarder class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os


class TestLineMessageForwarder:
    """Test LineMessageForwarder main functionality"""
    
    @patch('forwarder.LINE')
    def test_initialization(self, mock_line_class):
        """Test forwarder initialization"""
        mock_line_instance = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        target_groups = ['C123', 'C456']
        forwarder = LineMessageForwarder(target_groups=target_groups)
        
        assert forwarder.target_groups == target_groups
        assert len(forwarder.group_settings) == 2
        assert 'C123' in forwarder.group_settings
        assert 'C456' in forwarder.group_settings
    
    @patch('forwarder.LINE')
    def test_initialization_without_groups(self, mock_line_class):
        """Test forwarder initialization without target groups"""
        mock_line_instance = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder()
        
        assert forwarder.target_groups == []
        assert forwarder.group_settings == {}
    
    @patch('forwarder.LINE')
    def test_is_monitored_group(self, mock_line_class):
        """Test monitored group checking"""
        mock_line_instance = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        target_groups = ['C123', 'C456']
        forwarder = LineMessageForwarder(target_groups=target_groups)
        
        assert forwarder.is_monitored_group('C123') is True
        assert forwarder.is_monitored_group('C456') is True
        assert forwarder.is_monitored_group('C789') is False
    
    @patch('forwarder.LINE')
    def test_group_settings_initialization(self, mock_line_class):
        """Test group settings are initialized correctly"""
        mock_line_instance = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        target_groups = ['C123']
        forwarder = LineMessageForwarder(target_groups=target_groups)
        
        settings = forwarder.group_settings['C123']
        
        assert settings['forward_mode'] is False
        assert settings['target_group_id'] is None
        assert settings['on_duty_user_id'] is None
        assert settings['on_duty_user_name'] is None
    
    @patch('forwarder.LINE')
    def test_temp_images_directory_creation(self, mock_line_class):
        """Test that temp_images directory is created"""
        mock_line_instance = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        # Clean up if exists
        import shutil
        if os.path.exists('temp_images'):
            shutil.rmtree('temp_images')
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        assert os.path.exists('temp_images')
        
        # Clean up
        if os.path.exists('temp_images'):
            shutil.rmtree('temp_images')
    
    @patch('forwarder.LINE')
    def test_get_group_name(self, mock_line_class):
        """Test getting group name"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_class.return_value = mock_line_instance
        
        mock_group = MagicMock()
        mock_group.name = 'Test Group'
        mock_talk.getGroup.return_value = mock_group
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        group_name = forwarder.get_group_name('C123')
        
        assert group_name == 'Test Group'
    
    @patch('forwarder.LINE')
    def test_get_group_name_exception_handling(self, mock_line_class):
        """Test group name retrieval with exception"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_class.return_value = mock_line_instance
        
        mock_talk.getGroup.side_effect = Exception("API Error")
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        group_name = forwarder.get_group_name('C123')
        
        assert group_name == "未知群組"


class TestMessageHandling:
    """Test message handling functions"""
    
    @patch('forwarder.LINE')
    def test_handle_group_message_text(self, mock_line_class):
        """Test handling text messages in groups"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        # Create mock message
        message = MagicMock()
        message.type = 1  # Text message
        message.to = 'C123'  # Group ID
        message.text = 'Hello'
        
        # Should not raise exception
        forwarder.handle_group_message(message, 'U456', 'User Name')
    
    @patch('forwarder.LINE')
    def test_handle_group_message_not_monitored(self, mock_line_class):
        """Test that messages from non-monitored groups are ignored"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        message = MagicMock()
        message.type = 1
        message.to = 'C999'  # Not monitored
        message.text = 'Hello'
        
        forwarder.handle_group_message(message, 'U456', 'User Name')
        
        # Talk.sendMessage should not be called
        mock_talk.sendMessage.assert_not_called()


class TestForwardSettings:
    """Test forward settings management"""
    
    @patch('forwarder.LINE')
    def test_forward_mode_toggle(self, mock_line_class):
        """Test toggling forward mode"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        assert forwarder.group_settings['C123']['forward_mode'] is False
        
        forwarder.group_settings['C123']['forward_mode'] = True
        
        assert forwarder.group_settings['C123']['forward_mode'] is True
    
    @patch('forwarder.LINE')
    def test_target_group_setting(self, mock_line_class):
        """Test setting target group"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        forwarder.group_settings['C123']['target_group_id'] = 'C456'
        
        assert forwarder.group_settings['C123']['target_group_id'] == 'C456'
