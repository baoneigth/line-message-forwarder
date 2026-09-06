"""
Process monitor for the LINE message forwarder.

``ProcessMonitor`` acts as a watchdog: it periodically checks whether the
main forwarder process is alive (via its PID and heartbeat file) and
restarts it automatically if it has crashed or stopped responding. To avoid
restart loops it enforces a restart limit within a time window; if that
limit is exceeded it enters a cooldown period before resuming normal
monitoring.
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a required dependency
    psutil = None


class ProcessMonitor:
    """Monitors a subprocess and restarts it automatically when it crashes."""

    def __init__(self,
                 command=None,
                 pid_file='data/forwarder.pid',
                 heartbeat_file='data/heartbeat.json',
                 log_file='data/process_monitor.log',
                 restart_history_file='data/restart_history.json',
                 heartbeat_timeout=120,
                 restart_limit=3,
                 restart_window=60,
                 cooldown_period=300,
                 check_interval=60):
        """
        Args:
            command: List of args used to launch the monitored process,
                e.g. ``[sys.executable, 'forwarder_enhanced.py']``.
            pid_file: File used to track the monitored process PID.
            heartbeat_file: Heartbeat JSON file written by the process.
            log_file: File to append restart/monitor events to.
            restart_history_file: JSON file persisting restart history.
            heartbeat_timeout: Seconds after which a stale heartbeat is
                considered a failure.
            restart_limit: Maximum number of restarts allowed inside
                ``restart_window`` seconds before entering cooldown.
            restart_window: Time window (seconds) used for ``restart_limit``.
            cooldown_period: Seconds to wait before resuming monitoring after
                the restart limit has been exceeded.
            check_interval: Seconds between watchdog health checks.
        """
        self.command = command or [sys.executable, 'forwarder_enhanced.py']
        self.pid_file = pid_file
        self.heartbeat_file = heartbeat_file
        self.log_file = log_file
        self.restart_history_file = restart_history_file
        self.heartbeat_timeout = heartbeat_timeout
        self.restart_limit = restart_limit
        self.restart_window = restart_window
        self.cooldown_period = cooldown_period
        self.check_interval = check_interval

        self._ensure_dirs()
        self.restart_history = self._load_restart_history()
        self.logger = self._build_logger()
        self._cooldown_until = 0
        self._stop_requested = False

    # -- setup helpers -----------------------------------------------
    def _ensure_dirs(self):
        for path in (self.pid_file, self.heartbeat_file, self.log_file,
                     self.restart_history_file):
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    def _build_logger(self):
        logger = logging.getLogger(f'process_monitor.{id(self)}')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'))
            logger.addHandler(handler)
        return logger

    def _load_restart_history(self):
        if os.path.exists(self.restart_history_file):
            try:
                with open(self.restart_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_restart_history(self):
        tmp_path = f'{self.restart_history_file}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.restart_history, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.restart_history_file)

    # -- pid file helpers ----------------------------------------------
    def _read_pid(self):
        if not os.path.exists(self.pid_file):
            return None
        try:
            with open(self.pid_file, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            return None

    def _write_pid(self, pid):
        with open(self.pid_file, 'w', encoding='utf-8') as f:
            f.write(str(pid))

    def _clear_pid(self):
        if os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
            except OSError:
                pass

    # -- health checks ---------------------------------------------------
    def is_process_running(self):
        """Return True if the monitored process's PID is alive."""
        pid = self._read_pid()
        if pid is None:
            return False
        if psutil is not None:
            return psutil.pid_exists(pid)
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def check_heartbeat(self):
        """Return True if the heartbeat file exists and is fresh enough."""
        if not os.path.exists(self.heartbeat_file):
            return False
        try:
            with open(self.heartbeat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        timestamp = data.get('timestamp')
        if timestamp is None:
            return False

        age = datetime.now().timestamp() - float(timestamp)
        return age <= self.heartbeat_timeout

    def is_healthy(self):
        """Return True if the process is running and its heartbeat is fresh."""
        return self.is_process_running() and self.check_heartbeat()

    # -- restart handling -------------------------------------------------
    def log_restart_event(self, reason):
        """Record a restart event, both in the log file and history file."""
        now = datetime.now().timestamp()
        event = {
            'timestamp': now,
            'time': datetime.now().isoformat(),
            'reason': reason,
        }
        self.restart_history.append(event)

        # Prune old entries so restart_history doesn't grow unboundedly over
        # the lifetime of a long-running monitor. Keep a safety margin (2x)
        # beyond the largest window we actually check against.
        retention = max(self.restart_window, self.cooldown_period) * 2
        self.restart_history = [
            e for e in self.restart_history
            if now - e['timestamp'] <= retention
        ]

        self._save_restart_history()
        self.logger.info('Restart triggered: %s', reason)
        return event

    def handle_restart_limit(self):
        """Check whether too many restarts have happened recently.

        Returns True if the monitor should pause (cooldown) instead of
        restarting again, False if a restart is allowed.
        """
        now = datetime.now().timestamp()

        if now < self._cooldown_until:
            return True

        recent_restarts = [
            event for event in self.restart_history
            if now - event['timestamp'] <= self.restart_window
        ]

        if len(recent_restarts) >= self.restart_limit:
            self._cooldown_until = now + self.cooldown_period
            self.logger.warning(
                'Restart limit (%s within %ss) exceeded, entering cooldown for %ss',
                self.restart_limit, self.restart_window, self.cooldown_period)
            return True

        return False

    def start_process(self):
        """Launch the monitored process and record its PID."""
        process = subprocess.Popen(self.command)
        self._write_pid(process.pid)
        self.logger.info('Started process (pid=%s): %s', process.pid,
                          ' '.join(self.command))
        return process

    def stop_process(self):
        """Stop the monitored process if it is running."""
        pid = self._read_pid()
        if pid is None:
            return False
        if psutil is not None and psutil.pid_exists(pid):
            try:
                psutil.Process(pid).terminate()
            except psutil.Error:
                pass
        else:
            try:
                os.kill(pid, 15)
            except OSError:
                pass
        self._clear_pid()
        return True

    def restart_process(self, reason='manual restart'):
        """Restart the monitored process, respecting the restart limit."""
        if self.handle_restart_limit():
            self.logger.warning('Restart skipped due to cooldown: %s', reason)
            return None

        self.log_restart_event(reason)
        self.stop_process()
        return self.start_process()

    def auto_restart_on_crash(self):
        """Restart the process automatically if it has crashed or hung.

        Returns the reason string if a restart was triggered, else None.
        """
        if not self.is_process_running():
            reason = 'process not running'
        elif not self.check_heartbeat():
            reason = 'heartbeat timeout'
        else:
            return None

        self.restart_process(reason=reason)
        return reason

    # -- watchdog loop ----------------------------------------------------
    def run(self, max_iterations=None):
        """Run the watchdog loop, checking process health periodically.

        Args:
            max_iterations: If set, stop after this many iterations
                (primarily useful for tests). ``None`` runs forever until
                :meth:`stop` is called or a ``KeyboardInterrupt`` occurs.
        """
        self._stop_requested = False
        if not self.is_process_running():
            self.start_process()

        iterations = 0
        try:
            while not self._stop_requested:
                self.auto_restart_on_crash()
                iterations += 1
                if max_iterations is not None and iterations >= max_iterations:
                    break
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info('Watchdog stopped by user')

    def stop(self):
        """Request the watchdog loop started by :meth:`run` to stop."""
        self._stop_requested = True


def main():
    monitor = ProcessMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
