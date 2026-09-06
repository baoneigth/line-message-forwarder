"""
Tests for ProcessManager
"""
import json
import os
from unittest.mock import MagicMock, patch

from process_manager import ProcessManager


def make_manager(tmp_path, **kwargs):
    defaults = dict(
        command=['true'],
        pid_file=str(tmp_path / 'forwarder.pid'),
        heartbeat_file=str(tmp_path / 'heartbeat.json'),
        stop_timeout=1,
    )
    defaults.update(kwargs)
    return ProcessManager(**defaults)


class TestProcessManagerLifecycle:
    def test_is_running_false_without_pid_file(self, tmp_path):
        manager = make_manager(tmp_path)
        assert manager.is_running() is False

    @patch('process_manager.subprocess')
    def test_start_service_writes_pid(self, mock_subprocess, tmp_path):
        manager = make_manager(tmp_path)
        mock_process = MagicMock()
        mock_process.pid = 4321
        mock_subprocess.Popen.return_value = mock_process

        result = manager.start_service()

        assert result is True
        with open(manager.pid_file, 'r', encoding='utf-8') as f:
            assert f.read().strip() == '4321'

    @patch('process_manager.subprocess')
    def test_start_service_when_already_running(self, mock_subprocess, tmp_path):
        manager = make_manager(tmp_path)
        manager.is_running = MagicMock(return_value=True)

        result = manager.start_service()

        assert result is False
        mock_subprocess.Popen.assert_not_called()

    def test_stop_service_when_not_running(self, tmp_path):
        manager = make_manager(tmp_path)
        result = manager.stop_service()
        assert result is False

    @patch('process_manager.psutil')
    def test_stop_service_terminates_process(self, mock_psutil, tmp_path):
        manager = make_manager(tmp_path)
        with open(manager.pid_file, 'w', encoding='utf-8') as f:
            f.write('555')

        mock_psutil.pid_exists.return_value = True
        mock_proc = MagicMock()
        mock_psutil.Process.return_value = mock_proc

        result = manager.stop_service()

        assert result is True
        mock_proc.terminate.assert_called_once()
        assert not os.path.exists(manager.pid_file)

    def test_restart_service_calls_stop_then_start(self, tmp_path):
        manager = make_manager(tmp_path)
        manager.stop_service = MagicMock()
        manager.start_service = MagicMock(return_value=True)

        manager.restart_service()

        manager.stop_service.assert_called_once()
        manager.start_service.assert_called_once()


class TestProcessManagerStatus:
    def test_get_status_not_running(self, tmp_path):
        manager = make_manager(tmp_path)
        status = manager.get_status()

        assert status['running'] is False
        assert status['pid'] is None

    @patch('process_manager.psutil')
    def test_get_status_running_includes_metrics(self, mock_psutil, tmp_path):
        manager = make_manager(tmp_path)
        with open(manager.pid_file, 'w', encoding='utf-8') as f:
            f.write('777')

        mock_psutil.pid_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.create_time.return_value = 1000.0
        mock_proc.memory_info.return_value = MagicMock(rss=1024 * 1024)
        mock_proc.cpu_percent.return_value = 1.5
        mock_psutil.Process.return_value = mock_proc

        status = manager.get_status()

        assert status['running'] is True
        assert status['pid'] == 777
        assert status['memory_rss_bytes'] == 1024 * 1024
        assert status['cpu_percent'] == 1.5

    def test_get_status_includes_heartbeat(self, tmp_path):
        manager = make_manager(tmp_path)
        with open(manager.heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump({'status': 'running', 'updated_at': 'now'}, f)

        status = manager.get_status()

        assert status['heartbeat']['status'] == 'running'


class TestProcessManagerCleanup:
    @patch('process_manager.psutil', None)
    def test_cleanup_zombies_without_psutil_returns_zero(self, tmp_path):
        manager = make_manager(tmp_path)
        assert manager.cleanup_zombies() == 0

    @patch('process_manager.os')
    @patch('process_manager.psutil')
    def test_cleanup_zombies_reaps_matching_children(self, mock_psutil, mock_os, tmp_path):
        mock_os.getpid.return_value = 100
        mock_os.path.dirname.return_value = ''
        mock_os.path.exists.return_value = True

        zombie_proc = MagicMock()
        zombie_proc.info = {'pid': 200, 'ppid': 100, 'status': 'zombie'}
        other_proc = MagicMock()
        other_proc.info = {'pid': 300, 'ppid': 999, 'status': 'sleeping'}

        mock_psutil.STATUS_ZOMBIE = 'zombie'
        mock_psutil.process_iter.return_value = [zombie_proc, other_proc]

        manager = ProcessManager(command=['true'],
                                  pid_file=str(tmp_path / 'forwarder.pid'),
                                  heartbeat_file=str(tmp_path / 'heartbeat.json'))

        cleaned = manager.cleanup_zombies()

        assert cleaned == 1
        mock_os.waitpid.assert_called_once_with(200, mock_os.WNOHANG)
