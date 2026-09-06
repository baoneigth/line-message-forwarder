"""
Tests for the web dashboard authorization helper.
"""
import importlib


def make_handler(module, headers=None):
    handler = module.DashboardRequestHandler.__new__(module.DashboardRequestHandler)
    handler.headers = headers or {}
    return handler


class TestDashboardAuthorization:
    def test_no_token_configured_denies_access(self, monkeypatch):
        monkeypatch.delenv('DASHBOARD_TOKEN', raising=False)
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard)

        assert handler._is_authorized() is False

    def test_correct_header_token_allows_access(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard, headers={'X-Dashboard-Token': 'secret123'})

        assert handler._is_authorized() is True

    def test_wrong_header_token_denies_access(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard, headers={'X-Dashboard-Token': 'nope'})

        assert handler._is_authorized() is False

    def test_missing_header_denies_access(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard)

        assert handler._is_authorized() is False

    def test_run_refuses_to_start_without_token(self, monkeypatch):
        monkeypatch.delenv('DASHBOARD_TOKEN', raising=False)
        import web_dashboard
        importlib.reload(web_dashboard)

        try:
            web_dashboard.run(port=0)
            assert False, 'expected SystemExit'
        except SystemExit as exc:
            assert exc.code == 1

    def test_run_binds_localhost_by_default(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        monkeypatch.delenv('DASHBOARD_HOST', raising=False)
        import web_dashboard
        importlib.reload(web_dashboard)

        captured = {}

        class FakeServer:
            def __init__(self, address, handler):
                captured['address'] = address

            def serve_forever(self):
                raise KeyboardInterrupt()

            def shutdown(self):
                pass

        monkeypatch.setattr(web_dashboard, 'HTTPServer', FakeServer)

        web_dashboard.run(port=8080)

        assert captured['address'] == ('127.0.0.1', 8080)

    def test_run_honors_dashboard_host_env_var(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        monkeypatch.setenv('DASHBOARD_HOST', '0.0.0.0')
        import web_dashboard
        importlib.reload(web_dashboard)

        captured = {}

        class FakeServer:
            def __init__(self, address, handler):
                captured['address'] = address

            def serve_forever(self):
                raise KeyboardInterrupt()

            def shutdown(self):
                pass

        monkeypatch.setattr(web_dashboard, 'HTTPServer', FakeServer)

        web_dashboard.run(port=8080)

        assert captured['address'] == ('0.0.0.0', 8080)
