"""
Integration tests for LineMessageForwarder
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestIntegration:
    """Integration tests for the full flow"""
    
    @patch('forwarder.LINE')
    def test_forward_mode_workflow(self, mock_line_class):
        """Test the complete forward mode workflow"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_instance.api = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        from config import FORWARD_COMMAND, STOP_COMMAND
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        # Simulate /forward command
        forward_message = MagicMock()
        forward_message.type = 1
        forward_message.to = 'C123'
        forward_message.text = FORWARD_COMMAND
        
        forwarder.handle_group_message(forward_message, 'U456', 'Admin')
        
        # Check if forward mode was toggled
        assert forwarder.group_settings['C123']['forward_mode'] is True
        
        # Simulate /stop command
        stop_message = MagicMock()
        stop_message.type = 1
        stop_message.to = 'C123'
        stop_message.text = STOP_COMMAND
        
        forwarder.handle_group_message(stop_message, 'U456', 'Admin')
        
        # Check if forward mode was stopped
        assert forwarder.group_settings['C123']['forward_mode'] is False
    
    @patch('forwarder.LINE')
    def test_multiple_groups_independence(self, mock_line_class):
        """Test that settings for different groups are independent"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_instance.api = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123', 'C456'])
        
        # Enable forward mode in C123
        forwarder.group_settings['C123']['forward_mode'] = True
        forwarder.group_settings['C123']['target_group_id'] = 'C789'
        
        # C456 settings should remain unchanged
        assert forwarder.group_settings['C456']['forward_mode'] is False
        assert forwarder.group_settings['C456']['target_group_id'] is None
        
        # C123 settings should be as set
        assert forwarder.group_settings['C123']['forward_mode'] is True
        assert forwarder.group_settings['C123']['target_group_id'] == 'C789'
    
    @patch('forwarder.LINE')
    def test_message_forwarding_tracking(self, mock_line_class):
        """Test that forwarded messages are tracked correctly"""
        mock_line_instance = MagicMock()
        mock_talk = MagicMock()
        mock_line_instance.talk = mock_talk
        mock_line_instance.api = MagicMock()
        mock_line_class.return_value = mock_line_instance
        
        from forwarder import LineMessageForwarder
        
        forwarder = LineMessageForwarder(target_groups=['C123'])
        
        # Set up forwarding
        forwarder.group_settings['C123']['forward_mode'] = True
        forwarder.group_settings['C123']['target_group_id'] = 'C456'
        
        # Create message
        message = MagicMock()
        message.type = 1
        message.to = 'C123'
        message.text = 'Test message'
        message.id = 'msg_123'
        
        forwarder._forward_text_message(message.text, message, 'User', 'C123')
        
        # Check that message is tracked
        assert 'C123' in forwarder.forwarded_message_map
        assert 'msg_123' in forwarder.forwarded_message_map['C123']
        
        tracked = forwarder.forwarded_message_map['C123']['msg_123']
        assert tracked['target_group_id'] == 'C456'
        assert tracked['type'] == 'text'
