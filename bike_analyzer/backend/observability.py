"""Unified observability setup with Sentry and OpenTelemetry tracing.

Provides correlated tracing between Sentry errors and Zipkin traces using
OpenTelemetry as the shared instrumentation layer.
"""

from __future__ import annotations

import logging

import sentry_sdk

logger = logging.getLogger(__name__)
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


def _patch_fastapi_instrumentation():
    """Patch opentelemetry-instrumentation-fastapi to handle _IncludedRouter objects.

    The `_IncludedRouter` class (used for mounted routers in Starlette) lacks the `path`
    attribute, which causes AttributeError in `_get_route_details` when handling
    `Match.PARTIAL` routes. This monkeypatches the function to handle this case.
    """
    try:
        from starlette.routing import Match, Route

        def _patched_get_route_details(scope):
            app = scope["app"]
            route = None

            for starlette_route in app.routes:
                match, _ = (
                    Route.matches(starlette_route, scope)
                    if isinstance(starlette_route, Route)
                    else starlette_route.matches(scope)
                )
                if match == Match.FULL:
                    try:
                        route = starlette_route.path
                    except AttributeError:
                        route = scope.get("path")
                    break
                if match == Match.PARTIAL:
                    try:
                        route = starlette_route.path
                    except AttributeError:
                        route = scope.get("path")

            return route

        import opentelemetry.instrumentation.fastapi as fastapi_instr

        fastapi_instr._get_route_details = _patched_get_route_details
    except Exception:
        logger.debug("OpenTelemetry route detail patching failed", exc_info=True)


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

    # Apply patch before instrumenting
    _patch_fastapi_instrumentation()

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
        logger.info("Sentry initialized with OpenTelemetry support")

    # === OPENTELEMETRY ===
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.otel_environment,
        }
    )

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
            logger.info("Zipkin exporter configured: %s", zipkin_endpoint)
        except Exception as e:
            logger.warning("Zipkin exporter init failed: %s", e)
    elif settings.otel_exporter_otlp_endpoint and OTLP_AVAILABLE and not is_dev:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
            )
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(otlp_exporter, schedule_delay_millis=5000, max_export_batch_size=100)
            )
            logger.info("OTLP exporter configured: %s", settings.otel_exporter_otlp_endpoint)
        except Exception as e:
            logger.warning("OTLP exporter init failed: %s", e)
    else:
        logger.info("No telemetry exporter configured - tracing disabled")

    # === FASTAPI INSTRUMENTATION ===
    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="metrics,health,docs,redoc,openapi",
        )

    logger.info("Zipkin + Sentry correlation ready")
