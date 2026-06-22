"""OpenTelemetry tracing setup with Jaeger exporter."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .settings import get_settings


def setup_tracing(app=None):
    settings = get_settings()
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.otel_environment,
        }
    )

    trace.set_tracer_provider(TracerProvider(resource=resource))

    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    span_processor = BatchSpanProcessor(exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="metrics,health,docs,redoc,openapi",
        )

    print(
        f"Jaeger Tracing (OpenTelemetry) initialized -> {settings.otel_exporter_otlp_endpoint}"
    )
