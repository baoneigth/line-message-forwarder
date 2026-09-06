"""
Heartbeat management for the LINE message forwarder.

The main process periodically writes a small JSON file (``data/heartbeat.json``)
recording that it is still alive. ``monitors.process_monitor.ProcessMonitor`` can
then check the timestamp inside this file to decide whether the process is
healthy or needs to be restarted.
"""
import json
import os
import threading
import time
from datetime import datetime


class HeartbeatManager:
    """Writes periodic heartbeat information to a JSON file."""

    def __init__(self, heartbeat_file='data/heartbeat.json', interval=30):
        """
        Args:
            heartbeat_file: Path to the heartbeat JSON file.
            interval: Number of seconds between automatic heartbeat updates.
        """
        self.heartbeat_file = heartbeat_file
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None

        directory = os.path.dirname(self.heartbeat_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def write_heartbeat(self, status='running', extra=None):
        """Write the current heartbeat state to disk.

        Args:
            status: Text describing the current process status.
            extra: Optional dict with additional fields to merge in.
        """
        data = {
            'pid': os.getpid(),
            'status': status,
            'timestamp': datetime.now().timestamp(),
            'updated_at': datetime.now().isoformat(),
        }
        if extra:
            data.update(extra)

        tmp_path = f'{self.heartbeat_file}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.heartbeat_file)
        return data

    def update_heartbeat(self):
        """Alias for :meth:`write_heartbeat`, kept for API clarity."""
        return self.write_heartbeat()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.write_heartbeat()
            except Exception:
                pass
            self._stop_event.wait(self.interval)

    def start(self):
        """Start writing heartbeats in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.write_heartbeat(status='starting')
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background heartbeat thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
        try:
            self.write_heartbeat(status='stopped')
        except Exception:
            pass
