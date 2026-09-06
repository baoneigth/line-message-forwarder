"""
Tests for HeartbeatManager
"""
import json
import os
import time

from heartbeat import HeartbeatManager


class TestHeartbeatManager:
    """Test HeartbeatManager functionality"""

    def test_write_heartbeat_creates_file(self, tmp_path):
        heartbeat_file = tmp_path / 'heartbeat.json'
        manager = HeartbeatManager(heartbeat_file=str(heartbeat_file))

        data = manager.write_heartbeat()

        assert heartbeat_file.exists()
        assert data['pid'] == os.getpid()
        assert data['status'] == 'running'
        assert 'timestamp' in data

    def test_write_heartbeat_custom_status_and_extra(self, tmp_path):
        heartbeat_file = tmp_path / 'heartbeat.json'
        manager = HeartbeatManager(heartbeat_file=str(heartbeat_file))

        manager.write_heartbeat(status='idle', extra={'group_count': 3})

        with open(heartbeat_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['status'] == 'idle'
        assert data['group_count'] == 3

    def test_update_heartbeat_is_alias(self, tmp_path):
        heartbeat_file = tmp_path / 'heartbeat.json'
        manager = HeartbeatManager(heartbeat_file=str(heartbeat_file))

        data = manager.update_heartbeat()

        assert heartbeat_file.exists()
        assert data['status'] == 'running'

    def test_creates_parent_directory(self, tmp_path):
        heartbeat_file = tmp_path / 'nested' / 'dir' / 'heartbeat.json'
        HeartbeatManager(heartbeat_file=str(heartbeat_file))

        assert (tmp_path / 'nested' / 'dir').exists()

    def test_start_and_stop_background_thread(self, tmp_path):
        heartbeat_file = tmp_path / 'heartbeat.json'
        manager = HeartbeatManager(heartbeat_file=str(heartbeat_file), interval=0.05)

        manager.start()
        time.sleep(0.2)
        manager.stop()

        with open(heartbeat_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['status'] == 'stopped'
