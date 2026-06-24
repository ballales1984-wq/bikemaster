"""Unified observability setup with Sentry and OpenTelemetry tracing.

Provides correlated tracing between Sentry errors and Zipkin traces using
OpenTelemetry as the shared instrumentation layer.
"""

from __future__ import annotations

import sentry_sdk
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

try:
    from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter
    ZIPKIN_AVAILABLE = True
except ImportError:
    ZIPKIN_AVAILABLE = False

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False


def init_observability(app=None):
    """Initialize Sentry and OpenTelemetry tracing with Zipkin exporter.

    Uses Sentry's OpenTelemetry instrumenter for automatic trace correlation.
    Errors captured by Sentry will include the trace_id linking to Zipkin.
    """
    from .settings import get_settings
    settings = get_settings()

    # Skip observability in test environment
    if settings.environment.lower() in ("test", "testing"):
        return

    def _default_span_details(scope):
        """Custom span details callback to handle _IncludedRouter objects."""
        if scope.get("type") != "http":
            return ("unknown", {})
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "/")
        if not path:
            path = "/"
        return (f"{method} {path}", {})

# === SENTRY ===
    sentry_dsn = settings.sentry_dsn.strip() if settings.sentry_dsn else ""
    if sentry_dsn and sentry_dsn.startswith("http") and sentry_dsn.count("/") >= 5:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
            ],
            instrumenter="otel",
            send_default_pii=False,
            attach_stacktrace=True,
        )
        print("Sentry initialized with OpenTelemetry support")

    # === OPENTELEMETRY ===
    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "deployment.environment": settings.otel_environment,
    })

    trace.set_tracer_provider(TracerProvider(resource=resource))

    # Skip telemetry in development without explicit endpoints
    is_dev = settings.environment.lower() in ("development", "dev", "local")
    
    # Zipkin exporter (preferred) or fallback to OTLP/Jaeger
    zipkin_endpoint = settings.otel_exporter_zipkin_endpoint or "http://localhost:9411/api/v2/spans"
    zipkin_endpoint = zipkin_endpoint.strip() if zipkin_endpoint else ""
    if zipkin_endpoint and ZIPKIN_AVAILABLE and not is_dev:
        try:
            zipkin_exporter = ZipkinExporter(endpoint=zipkin_endpoint)
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(zipkin_exporter, schedule_delay_millis=5000, max_export_batch_size=100)
            )
            print(f"Zipkin exporter configured: {zipkin_endpoint}")
        except Exception as e:
            print(f"Zipkin exporter init failed: {e}")
    elif settings.otel_exporter_otlp_endpoint and OTLP_AVAILABLE and not is_dev:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
            )
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(otlp_exporter, schedule_delay_millis=5000, max_export_batch_size=100)
            )
            print(f"OTLP exporter configured: {settings.otel_exporter_otlp_endpoint}")
        except Exception as e:
            print(f"OTLP exporter init failed: {e}")
    else:
        print("No telemetry exporter configured - tracing disabled")

    # === FASTAPI INSTRUMENTATION ===
    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="metrics,health,docs,redoc,openapi",
        )

    print("Zipkin + Sentry correlation ready")