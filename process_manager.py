"""
Process management CLI tool for the LINE message forwarder.

Provides start/stop/restart/status/cleanup operations for the forwarder
process, usable directly from the command line:

    python process_manager.py start
    python process_manager.py stop
    python process_manager.py restart
    python process_manager.py status
    python process_manager.py cleanup
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a required dependency
    psutil = None


class ProcessManager:
    """Manages the lifecycle of the forwarder process."""

    def __init__(self,
                 command=None,
                 pid_file='data/forwarder.pid',
                 heartbeat_file='data/heartbeat.json',
                 stop_timeout=10):
        """
        Args:
            command: List of args used to launch the forwarder process.
            pid_file: File used to track the managed process PID.
            heartbeat_file: Heartbeat JSON file written by the process.
            stop_timeout: Seconds to wait for graceful termination before
                forcefully killing the process.
        """
        self.command = command or [sys.executable, 'forwarder_enhanced.py']
        self.pid_file = pid_file
        self.heartbeat_file = heartbeat_file
        self.stop_timeout = stop_timeout

        directory = os.path.dirname(self.pid_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    # -- pid helpers -------------------------------------------------
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

    def is_running(self):
        """Return True if the managed process is currently alive."""
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

    # -- lifecycle -----------------------------------------------------
    def start_service(self):
        """Start the forwarder process if it isn't already running."""
        if self.is_running():
            print('[!] 服務已在運行中')
            return False

        process = subprocess.Popen(self.command)
        self._write_pid(process.pid)
        print(f'[✓] 服務已啟動 (pid={process.pid})')
        return True

    def stop_service(self):
        """Stop the forwarder process, waiting for a graceful shutdown."""
        pid = self._read_pid()
        if pid is None or not self.is_running():
            print('[!] 服務未在運行')
            self._clear_pid()
            return False

        if psutil is not None:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=self.stop_timeout)
            except psutil.TimeoutExpired:
                proc.kill()
            except psutil.Error:
                pass
        else:
            try:
                os.kill(pid, 15)
                time.sleep(self.stop_timeout)
            except OSError:
                pass

        self._clear_pid()
        print('[✓] 服務已停止')
        return True

    def restart_service(self):
        """Stop then start the forwarder process."""
        self.stop_service()
        return self.start_service()

    def get_status(self):
        """Return a dict describing the current service status."""
        pid = self._read_pid()
        running = self.is_running()

        status = {
            'running': running,
            'pid': pid if running else None,
        }

        if running and psutil is not None:
            try:
                proc = psutil.Process(pid)
                status['uptime_seconds'] = time.time() - proc.create_time()
                status['memory_rss_bytes'] = proc.memory_info().rss
                status['cpu_percent'] = proc.cpu_percent(interval=0.1)
            except psutil.Error:
                pass

        if os.path.exists(self.heartbeat_file):
            try:
                with open(self.heartbeat_file, 'r', encoding='utf-8') as f:
                    status['heartbeat'] = json.load(f)
            except (json.JSONDecodeError, OSError):
                status['heartbeat'] = None

        return status

    def cleanup_zombies(self):
        """Reap zombie/defunct child processes belonging to this manager.

        Returns the number of zombie processes cleaned up.
        """
        if psutil is None:
            return 0

        cleaned = 0
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'ppid', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE and \
                        proc.info['ppid'] == current_pid:
                    os.waitpid(proc.info['pid'], os.WNOHANG)
                    cleaned += 1
            except (psutil.NoSuchProcess, ChildProcessError, OSError):
                continue
        return cleaned


def _print_status(status):
    print('[狀態]')
    print(f"  運行中: {'是' if status['running'] else '否'}")
    if status.get('pid'):
        print(f"  PID: {status['pid']}")
    if 'uptime_seconds' in status:
        print(f"  運行時間: {status['uptime_seconds']:.0f} 秒")
    if 'memory_rss_bytes' in status:
        print(f"  記憶體占用: {status['memory_rss_bytes'] / 1024 / 1024:.1f} MB")
    if status.get('heartbeat'):
        print(f"  最後心跳: {status['heartbeat'].get('updated_at')}")


def main():
    if len(sys.argv) < 2:
        print('用法: python process_manager.py [start|stop|restart|status|cleanup]')
        sys.exit(1)

    action = sys.argv[1]
    manager = ProcessManager()

    if action == 'start':
        manager.start_service()
    elif action == 'stop':
        manager.stop_service()
    elif action == 'restart':
        manager.restart_service()
    elif action == 'status':
        _print_status(manager.get_status())
    elif action == 'cleanup':
        count = manager.cleanup_zombies()
        print(f'[✓] 已清理 {count} 個殭屍進程')
    else:
        print(f'[!] 未知指令: {action}')
        sys.exit(1)


if __name__ == '__main__':
    main()
