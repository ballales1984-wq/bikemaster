"""Tests for monitoring module."""

import pytest

from bike_analyzer.backend.monitoring import (
    PROMETHEUS_AVAILABLE,
    http_request_duration_seconds,
    http_requests_total,
)


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
class TestHttpRequestsTotal:
    def test_counter_exists(self):
        assert http_requests_total is not None

    def test_counter_has_labels(self):
        assert hasattr(http_requests_total, "labels")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
class TestHttpRequestDuration:
    def test_histogram_exists(self):
        assert http_request_duration_seconds is not None

    def test_histogram_has_labels(self):
        assert hasattr(http_request_duration_seconds, "labels")


class TestPrometheusAvailability:
    def test_prometheus_flag(self):
        assert isinstance(PROMETHEUS_AVAILABLE, bool)
