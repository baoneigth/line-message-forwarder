"""
Enhanced entrypoint for the LINE message forwarder.

This module wraps :class:`forwarder.LineMessageForwarder` and adds a
background heartbeat so that an external watchdog (see
``monitors/process_monitor.py``) can detect whether the process is alive and
restart it automatically if it stops responding or crashes.
"""
import sys

from forwarder import LineMessageForwarder
from heartbeat import HeartbeatManager

HEARTBEAT_FILE = 'data/heartbeat.json'
HEARTBEAT_INTERVAL = 30


class EnhancedLineMessageForwarder(LineMessageForwarder):
    """LineMessageForwarder with heartbeat support."""

    def __init__(self, target_groups=None, heartbeat_file=HEARTBEAT_FILE,
                 heartbeat_interval=HEARTBEAT_INTERVAL):
        self.heartbeat = HeartbeatManager(heartbeat_file=heartbeat_file,
                                           interval=heartbeat_interval)
        super().__init__(target_groups=target_groups)

    def start(self):
        """Start the heartbeat thread, then run the normal message loop."""
        self.heartbeat.start()
        try:
            super().start()
        finally:
            self.heartbeat.stop()


def main():
    # 在這裡指定要監聽的群組 ID
    # 例如: ['C0abc123...', 'C0def456...', ...]
    target_groups = [
        # 請在此處添加您要監聽的群組 ID
        # 'C0abc123...',
        # 'C0def456...',
    ]

    if not target_groups:
        print("[!] 錯誤: 請在 main() 函數中指定要監聽的群組 ID")
        print("[*] 使用方式:")
        print("    target_groups = ['C0abc123...', 'C0def456...', ...]")
        sys.exit(1)

    forwarder = EnhancedLineMessageForwarder(target_groups=target_groups)
    forwarder.start()


if __name__ == '__main__':
    main()
