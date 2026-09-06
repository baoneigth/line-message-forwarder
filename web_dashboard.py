"""
Simple web dashboard for monitoring and controlling the LINE message
forwarder process.

Implemented using only the Python standard library (``http.server``) to
avoid adding a new runtime dependency. Run with:

    python web_dashboard.py [port]

Available API endpoints:
    GET  /api/process/status           - current process status
    GET  /api/process/uptime           - process uptime in seconds
    GET  /api/process/memory           - process memory usage
    GET  /api/process/restart-history  - restart history log
    POST /api/process/restart          - manually restart the process
    POST /api/process/stop             - manually stop the process

Authentication:
    Control endpoints (POST /api/process/restart, POST /api/process/stop)
    require a token when the ``DASHBOARD_TOKEN`` environment variable is
    set. Clients must send it as the ``X-Dashboard-Token`` header (or a
    ``?token=`` query parameter). If ``DASHBOARD_TOKEN`` is not set, control
    endpoints are disabled by default to avoid exposing unauthenticated
    process control on the network.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from process_manager import ProcessManager

RESTART_HISTORY_FILE = 'data/restart_history.json'
DASHBOARD_TOKEN = os.environ.get('DASHBOARD_TOKEN')

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>LINE Forwarder 監控儀表板</title>
</head>
<body>
<h1>LINE Forwarder 監控儀表板</h1>
<p>API Token: <input id="token" type="password" placeholder="DASHBOARD_TOKEN"></p>
<div id="status">載入中...</div>
<button onclick="callApi('/api/process/restart')">重啟</button>
<button onclick="callApi('/api/process/stop')">停止</button>
<script>
function token() { return document.getElementById('token').value; }
async function refresh() {
  const res = await fetch('/api/process/status');
  const data = await res.json();
  document.getElementById('status').innerText = JSON.stringify(data, null, 2);
}
async function callApi(path) {
  await fetch(path, { method: 'POST', headers: { 'X-Dashboard-Token': token() } });
  refresh();
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


def load_restart_history():
    if not os.path.exists(RESTART_HISTORY_FILE):
        return []
    try:
        with open(RESTART_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


class DashboardRequestHandler(BaseHTTPRequestHandler):
    manager = ProcessManager()

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _is_authorized(self, parsed):
        """Check the request against DASHBOARD_TOKEN, if one is configured."""
        if not DASHBOARD_TOKEN:
            return False
        supplied = self.headers.get('X-Dashboard-Token')
        if not supplied:
            query = parse_qs(parsed.query)
            supplied = query.get('token', [None])[0]
        return supplied == DASHBOARD_TOKEN

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/':
            self._send_html(DASHBOARD_HTML)
        elif path == '/api/process/status':
            self._send_json(self.manager.get_status())
        elif path == '/api/process/uptime':
            status = self.manager.get_status()
            self._send_json({'uptime_seconds': status.get('uptime_seconds', 0)})
        elif path == '/api/process/memory':
            status = self.manager.get_status()
            self._send_json({'memory_rss_bytes': status.get('memory_rss_bytes', 0)})
        elif path == '/api/process/restart-history':
            self._send_json({'history': load_restart_history()})
        else:
            self._send_json({'error': 'not found'}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path not in ('/api/process/restart', '/api/process/stop'):
            self._send_json({'error': 'not found'}, status=404)
            return

        if not self._is_authorized(parsed):
            self._send_json(
                {'error': 'unauthorized: set DASHBOARD_TOKEN and send it as '
                          'X-Dashboard-Token header or ?token= query param'},
                status=401)
            return

        if path == '/api/process/restart':
            self.manager.restart_service()
            self._send_json({'result': 'restarted'})
        else:
            self.manager.stop_service()
            self._send_json({'result': 'stopped'})

    def log_message(self, format, *args):  # noqa: A002 - match base class signature
        pass


def run(port=8080):
    server = HTTPServer(('0.0.0.0', port), DashboardRequestHandler)
    print(f'[*] Web 儀表板已啟動: http://0.0.0.0:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 8080)
