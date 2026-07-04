"""Tests for observability module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from bike_analyzer.backend.observability import (
    _patch_fastapi_instrumentation,
    init_observability,
)


class TestPatchFastapiInstrumentation:
    def test_patch_applies_successfully(self):
        mock_fastapi_instr = MagicMock()
        with patch.dict(
            sys.modules,
            {
                "starlette.routing": MagicMock(),
                "opentelemetry.instrumentation.fastapi": mock_fastapi_instr,
            },
        ):
            _patch_fastapi_instrumentation()
            assert mock_fastapi_instr._get_route_details is not None

    def test_patch_handles_import_error(self):
        with patch.dict(
            sys.modules,
            {
                "starlette.routing": None,
            },
        ):
            _patch_fastapi_instrumentation()


class TestInitObservability:
    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_skips_test_environment(self, mock_get_settings, mock_instr):
        mock_settings = MagicMock()
        mock_settings.environment = "test"
        mock_settings.sentry_dsn = "http://key@o123.ingest.sentry.io/456"
        mock_settings.sentry_environment = "test"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "test"
        mock_settings.otel_exporter_zipkin_endpoint = ""
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        with patch("bike_analyzer.backend.observability.sentry_sdk.init") as mock_sentry:
            init_observability()
            mock_sentry.assert_not_called()

    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_initializes_sentry_with_valid_dsn(self, mock_get_settings, mock_instr):
        import sentry_sdk

        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.sentry_dsn = "https://abc@o123.ingest.sentry.io/api/proj/456"
        mock_settings.sentry_environment = "production"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "production"
        mock_settings.otel_exporter_zipkin_endpoint = ""
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        with patch.object(sentry_sdk, "init", return_value=None) as mock_sentry:
            with patch("bike_analyzer.backend.observability.trace.set_tracer_provider"):
                init_observability()
                mock_sentry.assert_called_once()
                call_kwargs = mock_sentry.call_args.kwargs
                assert call_kwargs["dsn"] == "https://abc@o123.ingest.sentry.io/api/proj/456"
                assert call_kwargs["environment"] == "production"
                assert call_kwargs["instrumenter"] == "otel"

    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_skips_sentry_with_invalid_dsn(self, mock_get_settings, mock_instr):
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.sentry_dsn = "not-a-valid-dsn"
        mock_settings.sentry_environment = "production"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "production"
        mock_settings.otel_exporter_zipkin_endpoint = ""
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        with patch("bike_analyzer.backend.observability.sentry_sdk.init") as mock_sentry:
            init_observability()
            mock_sentry.assert_not_called()

    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_sets_tracer_provider(self, mock_get_settings, mock_instr):
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.sentry_dsn = ""
        mock_settings.sentry_environment = "production"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "production"
        mock_settings.otel_exporter_zipkin_endpoint = ""
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        with patch("bike_analyzer.backend.observability.trace") as mock_trace:
            init_observability()
            mock_trace.set_tracer_provider.assert_called_once()

    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_with_app_instrumentation(self, mock_get_settings, mock_instr):
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.sentry_dsn = ""
        mock_settings.sentry_environment = "production"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "production"
        mock_settings.otel_exporter_zipkin_endpoint = ""
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        mock_app = MagicMock()
        with patch("bike_analyzer.backend.observability.trace"):
            init_observability(app=mock_app)
            mock_instr.instrument_app.assert_called_once()

    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_development_env_skips_exporters(self, mock_get_settings, mock_instr):
        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.sentry_dsn = ""
        mock_settings.sentry_environment = "production"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "development"
        mock_settings.otel_exporter_zipkin_endpoint = ""
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        with patch("bike_analyzer.backend.observability.trace"):
            init_observability()

    @patch("bike_analyzer.backend.observability.FastAPIInstrumentor")
    @patch("bike_analyzer.backend.settings.get_settings")
    def test_instruments_app_when_provided(self, mock_get_settings, mock_instr):
        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.sentry_dsn = ""
        mock_settings.sentry_environment = "production"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1
        mock_settings.otel_service_name = "test-service"
        mock_settings.otel_environment = "production"
        mock_settings.otel_exporter_zipkin_endpoint = "http://localhost:9411"
        mock_settings.otel_exporter_otlp_endpoint = ""
        mock_get_settings.return_value = mock_settings

        mock_app = MagicMock()
        with patch("bike_analyzer.backend.observability.ZIPKIN_AVAILABLE", False):
            with patch("bike_analyzer.backend.observability.trace"):
                init_observability(app=mock_app)
                mock_instr.instrument_app.assert_called_once()
