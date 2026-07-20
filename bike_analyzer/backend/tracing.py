"""OpenTelemetry tracing setup with Jaeger exporter."""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .settings import get_settings

logger = logging.getLogger(__name__)

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False


def setup_tracing(app=None):
    """Configures the OpenTelemetry tracer (export to OTLP/Jaeger).

    Registers a ``TracerProvider`` with service resources from ``Settings`` and,
    if ``otel_exporter_otlp_endpoint`` is configured, attaches a ``BatchSpanProcessor``
    with insecure OTLP exporter. If the endpoint is missing or the dependency is not
    available, tracing remains disabled without interrupting startup.
    ``app`` is accepted for signature consistency but not yet instrumented here.
    """
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
            logger.info("Jaeger Tracing (OpenTelemetry) initialized -> %s", settings.otel_exporter_otlp_endpoint)
        except Exception as e:
            logger.warning("OTLP exporter init failed (tracing disabled): %s", e)
    else:
        logger.info("No OTLP endpoint configured - tracing disabled")


