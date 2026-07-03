"""Tests for tracing module."""

from unittest.mock import MagicMock, patch

from bike_analyzer.backend.tracing import setup_tracing


class TestSetupTracing:
    def test_setup_tracing_no_otlp(self, monkeypatch):
        monkeypatch.setattr("bike_analyzer.backend.tracing.OTLP_AVAILABLE", False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

        with patch("bike_analyzer.backend.tracing.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.otel_service_name = "test-service"
            mock_settings_obj.otel_environment = "test"
            mock_settings_obj.otel_exporter_otlp_endpoint = ""
            mock_settings.return_value = mock_settings_obj

            result = setup_tracing()
            assert result is None

    @patch("bike_analyzer.backend.tracing.get_settings")
    def test_setup_tracing_with_otlp_disabled_endpoint(self, mock_settings):
        mock_settings_obj = MagicMock()
        mock_settings_obj.otel_service_name = "test-service"
        mock_settings_obj.otel_environment = "test"
        mock_settings_obj.otel_exporter_otlp_endpoint = ""
        mock_settings.return_value = mock_settings_obj

        result = setup_tracing()
        assert result is None
