"""Unified observability setup with Sentry and OpenTelemetry tracing.

Provides correlated tracing between Sentry errors and Zipkin traces using
OpenTelemetry as the shared instrumentation layer.
"""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

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

    # === SENTRY ===
    if settings.sentry_dsn and settings.sentry_dsn.strip():
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
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

    # Zipkin exporter (preferred) or fallback to OTLP/Jaeger
    zipkin_endpoint = settings.otel_exporter_zipkin_endpoint or "http://localhost:9411/api/v2/spans"
    zipkin_endpoint = zipkin_endpoint.strip() if zipkin_endpoint else ""
    if zipkin_endpoint and ZIPKIN_AVAILABLE:
        zipkin_exporter = ZipkinExporter(endpoint=zipkin_endpoint)
        trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(zipkin_exporter))
        print(f"Zipkin exporter configured: {zipkin_endpoint}")
    elif settings.otel_exporter_otlp_endpoint and OTLP_AVAILABLE:
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
        print(f"OTLP exporter configured: {settings.otel_exporter_otlp_endpoint}")

    # === FASTAPI INSTRUMENTATION ===
    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="metrics,health,docs,redoc,openapi",
        )

    print("Zipkin + Sentry correlation ready")