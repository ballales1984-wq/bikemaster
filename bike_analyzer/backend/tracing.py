"""OpenTelemetry tracing setup with Jaeger exporter."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .settings import get_settings

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False


def setup_tracing(app=None):
    settings = get_settings()
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.otel_environment,
        }
    )

    trace.set_tracer_provider(TracerProvider(resource=resource))

    if settings.otel_exporter_otlp_endpoint and OTLP_AVAILABLE:
        try:
            exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
            )
            trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))
            print(f"Jaeger Tracing (OpenTelemetry) initialized -> {settings.otel_exporter_otlp_endpoint}")
        except Exception as e:
            print(f"OTLP exporter init failed (tracing disabled): {e}")
    else:
        print("No OTLP endpoint configured - tracing disabled")
