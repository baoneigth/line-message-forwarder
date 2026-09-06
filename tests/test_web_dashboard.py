"""
Tests for the web dashboard authorization helper.
"""
import importlib
from unittest.mock import MagicMock
from urllib.parse import urlparse


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
        parsed = urlparse('/api/process/restart')

        assert handler._is_authorized(parsed) is False

    def test_correct_header_token_allows_access(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard, headers={'X-Dashboard-Token': 'secret123'})
        parsed = urlparse('/api/process/restart')

        assert handler._is_authorized(parsed) is True

    def test_wrong_header_token_denies_access(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard, headers={'X-Dashboard-Token': 'nope'})
        parsed = urlparse('/api/process/restart')

        assert handler._is_authorized(parsed) is False

    def test_query_param_token_allows_access(self, monkeypatch):
        monkeypatch.setenv('DASHBOARD_TOKEN', 'secret123')
        import web_dashboard
        importlib.reload(web_dashboard)

        handler = make_handler(web_dashboard)
        parsed = urlparse('/api/process/restart?token=secret123')

        assert handler._is_authorized(parsed) is True
