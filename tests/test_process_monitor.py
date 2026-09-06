"""
Tests for ProcessMonitor
"""
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from monitors.process_monitor import ProcessMonitor


def make_monitor(tmp_path, **kwargs):
    defaults = dict(
        command=['true'],
        pid_file=str(tmp_path / 'forwarder.pid'),
        heartbeat_file=str(tmp_path / 'heartbeat.json'),
        log_file=str(tmp_path / 'process_monitor.log'),
        restart_history_file=str(tmp_path / 'restart_history.json'),
        heartbeat_timeout=120,
        restart_limit=3,
        restart_window=60,
        cooldown_period=300,
        check_interval=0.01,
    )
    defaults.update(kwargs)
    return ProcessMonitor(**defaults)


class TestProcessMonitorHeartbeat:
    def test_check_heartbeat_missing_file(self, tmp_path):
        monitor = make_monitor(tmp_path)
        assert monitor.check_heartbeat() is False

    def test_check_heartbeat_fresh(self, tmp_path):
        monitor = make_monitor(tmp_path)
        with open(monitor.heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time()}, f)

        assert monitor.check_heartbeat() is True

    def test_check_heartbeat_stale(self, tmp_path):
        monitor = make_monitor(tmp_path, heartbeat_timeout=5)
        with open(monitor.heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time() - 100}, f)

        assert monitor.check_heartbeat() is False

    def test_check_heartbeat_corrupt_file(self, tmp_path):
        monitor = make_monitor(tmp_path)
        with open(monitor.heartbeat_file, 'w', encoding='utf-8') as f:
            f.write('not json')

        assert monitor.check_heartbeat() is False


class TestProcessMonitorRestartLimit:
    def test_no_restarts_allows_restart(self, tmp_path):
        monitor = make_monitor(tmp_path)
        assert monitor.handle_restart_limit() is False

    def test_exceeding_limit_triggers_cooldown(self, tmp_path):
        monitor = make_monitor(tmp_path, restart_limit=2, restart_window=60,
                                cooldown_period=300)
        monitor.log_restart_event('crash 1')
        monitor.log_restart_event('crash 2')

        assert monitor.handle_restart_limit() is True

    def test_old_restarts_outside_window_are_ignored(self, tmp_path):
        monitor = make_monitor(tmp_path, restart_limit=2, restart_window=60)
        old_event = {
            'timestamp': time.time() - 1000,
            'time': 'old',
            'reason': 'old crash',
        }
        monitor.restart_history.append(old_event)
        monitor._save_restart_history()

        assert monitor.handle_restart_limit() is False

    def test_log_restart_event_persists_to_file(self, tmp_path):
        monitor = make_monitor(tmp_path)
        monitor.log_restart_event('test crash')

        with open(monitor.restart_history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        assert len(history) == 1
        assert history[0]['reason'] == 'test crash'


class TestProcessMonitorProcessControl:
    def test_is_process_running_no_pid_file(self, tmp_path):
        monitor = make_monitor(tmp_path)
        assert monitor.is_process_running() is False

    @patch('monitors.process_monitor.psutil')
    def test_is_process_running_with_pid_file(self, mock_psutil, tmp_path):
        monitor = make_monitor(tmp_path)
        with open(monitor.pid_file, 'w', encoding='utf-8') as f:
            f.write('12345')

        mock_psutil.pid_exists.return_value = True
        assert monitor.is_process_running() is True
        mock_psutil.pid_exists.assert_called_once_with(12345)

    @patch('monitors.process_monitor.subprocess')
    def test_start_process_writes_pid(self, mock_subprocess, tmp_path):
        monitor = make_monitor(tmp_path)
        mock_process = MagicMock()
        mock_process.pid = 9999
        mock_subprocess.Popen.return_value = mock_process

        monitor.start_process()

        with open(monitor.pid_file, 'r', encoding='utf-8') as f:
            assert f.read().strip() == '9999'

    def test_auto_restart_on_crash_when_not_running(self, tmp_path):
        monitor = make_monitor(tmp_path)
        monitor.start_process = MagicMock()
        monitor.stop_process = MagicMock()

        reason = monitor.auto_restart_on_crash()

        assert reason == 'process not running'
        monitor.start_process.assert_called_once()

    def test_auto_restart_on_crash_when_healthy(self, tmp_path):
        monitor = make_monitor(tmp_path)
        monitor.is_process_running = MagicMock(return_value=True)
        monitor.check_heartbeat = MagicMock(return_value=True)
        monitor.start_process = MagicMock()

        reason = monitor.auto_restart_on_crash()

        assert reason is None
        monitor.start_process.assert_not_called()

    def test_auto_restart_respects_cooldown(self, tmp_path):
        monitor = make_monitor(tmp_path, restart_limit=1, restart_window=60,
                                cooldown_period=300)
        monitor.start_process = MagicMock()
        monitor.stop_process = MagicMock()
        monitor.is_process_running = MagicMock(return_value=False)

        # First crash triggers a restart and hits the limit
        monitor.auto_restart_on_crash()
        assert monitor.start_process.call_count == 1

        # Second crash should be suppressed by cooldown
        monitor.auto_restart_on_crash()
        assert monitor.start_process.call_count == 1


class TestProcessMonitorRun:
    def test_run_stops_after_max_iterations(self, tmp_path):
        monitor = make_monitor(tmp_path, check_interval=0)
        monitor.is_process_running = MagicMock(return_value=True)
        monitor.check_heartbeat = MagicMock(return_value=True)
        monitor.start_process = MagicMock()

        monitor.run(max_iterations=3)

        # process already running/healthy, so start_process should not be
        # called again after the initial startup check
        assert monitor.start_process.call_count == 0
