"""Tests for MetricsMiddleware and tracing module."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bike_analyzer.backend.tracing import OTLP_AVAILABLE, setup_tracing
from bike_analyzer.backend.monitoring import MetricsMiddleware


class TestMetricsMiddleware:
    def test_init(self):
        app = MagicMock()
        middleware = MetricsMiddleware(app)
        assert middleware.app is app

    @pytest.mark.asyncio
    async def test_non_http_request(self):
        app = MagicMock()
        app_call = AsyncMock()
        middleware = MetricsMiddleware(app_call)
        scope = {"type": "websocket"}
        receive = MagicMock()
        send = MagicMock()
        await middleware(scope, receive, send)
        app_call.dispatch_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_request_tracks_metrics(self):
        app = AsyncMock()
        middleware = MetricsMiddleware(app)
        scope = {"type": "http", "method": "GET", "path": "/api/test"}
        receive = MagicMock()
        send = MagicMock()

        async def mock_send(message):
            if message["type"] == "http.response.start":
                message["status"] = 200

        with patch("bike_analyzer.backend.monitoring.record_http_request") as mock_record:
            await middleware(scope, receive, mock_send)
            assert mock_record.called

    @pytest.mark.asyncio
    async def test_http_request_tracks_duration(self):
        app = AsyncMock()
        middleware = MetricsMiddleware(app)
        scope = {"type": "http", "method": "POST", "path": "/api/rides"}
        receive = MagicMock()
        send = MagicMock()

        async def mock_send(message):
            if message["type"] == "http.response.start":
                time.sleep(0.01)

        with patch("bike_analyzer.backend.monitoring.record_http_request") as mock_record:
            await middleware(scope, receive, mock_send)
            call_args = mock_record.call_args[0]
            assert len(call_args) >= 3
            duration = call_args[2]
            assert duration >= 0.01


class TestSetupTracing:
    @patch("bike_analyzer.backend.tracing.get_settings")
    def test_no_otlp_available(self, mock_settings):
        mock_settings_obj = MagicMock()
        mock_settings_obj.otel_service_name = "test"
        mock_settings_obj.otel_environment = "test"
        mock_settings_obj.otel_exporter_otlp_endpoint = "http://localhost:4317"
        mock_settings.return_value = mock_settings_obj
        with patch("bike_analyzer.backend.tracing.OTLP_AVAILABLE", False):
            result = setup_tracing()
            assert result is None
