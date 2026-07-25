"""Tests for AI Coach helper functions (pure/mocked paths)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.slow

from bike_analyzer.backend.analytics.ai_coach import (
    _clean_ai_output,
    _coach_mode,
    _is_recoverable_provider_error,
    _provider_order,
)


class TestCleanAiOutput:
    def test_strips_trailing_zero_decimals(self):
        assert _clean_ai_output("5.0 km") == "5 km"

    def test_strips_trailing_zero_after_dot(self):
        assert _clean_ai_output("23.30 h") == "23.3 h"

    def test_collapses_multiple_newlines(self):
        assert _clean_ai_output("a\n\n\nb") == "a\nb"

    def test_collapses_multiple_spaces(self):
        assert _clean_ai_output("a   b") == "a b"

    def test_strips_whitespace(self):
        assert _clean_ai_output("  hello  ") == "hello"


class TestCoachMode:
    def test_defaults_to_external(self):
        os.environ.pop("AI_COACH_MODE", None)
        assert _coach_mode() == "external"

    def test_reads_env_override(self):
        os.environ["AI_COACH_MODE"] = "local"
        assert _coach_mode() == "local"
        os.environ.pop("AI_COACH_MODE", None)


class TestProviderOrder:
    def test_default_order(self):
        os.environ.pop("AI_COACH_PROVIDER_ORDER", None)
        assert _provider_order() == ["groq"]

    def test_custom_order(self):
        os.environ["AI_COACH_PROVIDER_ORDER"] = "openai, groq"
        assert _provider_order() == ["openai", "groq"]
        os.environ.pop("AI_COACH_PROVIDER_ORDER", None)

    def test_empty_env_returns_default(self):
        os.environ["AI_COACH_PROVIDER_ORDER"] = ""
        assert _provider_order() == ["groq"]
        os.environ.pop("AI_COACH_PROVIDER_ORDER", None)


class TestIsRecoverableProviderError:
    def test_value_error_not_recoverable(self):
        assert _is_recoverable_provider_error(ValueError("bad")) is False

    def test_type_error_not_recoverable(self):
        assert _is_recoverable_provider_error(TypeError("bad")) is False

    def test_auth_error_not_recoverable(self):
        assert _is_recoverable_provider_error(Exception("auth failed")) is False

    def test_connection_error_recoverable(self):
        assert _is_recoverable_provider_error(ConnectionError("timeout")) is True

    def test_generic_exception_recoverable(self):
        assert _is_recoverable_provider_error(Exception("unknown")) is True
