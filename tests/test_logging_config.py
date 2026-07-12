"""Tests for structured logging configuration."""

from __future__ import annotations

import logging

import pytest

from bike_analyzer.backend.logging_config import setup_logging


def test_setup_logging_does_not_raise():
    setup_logging()
    logger = logging.getLogger("test_logging")
    logger.info("test message")
    assert True


def test_json_formatter_outputs_json_when_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LOG_FORMAT", "json")
    setup_logging()
    logger = logging.getLogger("test_json_logger")
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("hello world")
    assert True


def test_request_id_filter_adds_field(monkeypatch: pytest.MonkeyPatch):
    from bike_analyzer.backend import logging_config as lc

    monkeypatch.setenv("LOG_FORMAT", "json")
    setup_logging()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="msg",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc-123"
    filt = lc._RequestIdFilter()
    assert filt.filter(record) is True
    assert record.request_id == "abc-123"


def test_request_id_falls_back_to_context(monkeypatch: pytest.MonkeyPatch):
    from bike_analyzer.backend import logging_config as lc

    monkeypatch.setenv("LOG_FORMAT", "json")
    setup_logging()
    with lc.request_context("req-xyz"):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        filt = lc._RequestIdFilter()
        assert filt.filter(record) is True
        assert record.request_id == "req-xyz"


def test_request_id_context_default_is_dash():
    from bike_analyzer.backend import logging_config as lc

    assert lc.get_request_id() == "-"


def test_utils_logger_delegates_to_logging_config():
    from bike_analyzer.backend.utils.logger import get_logger

    log = get_logger("bike_analyzer.test.delegate")
    assert isinstance(log, logging.Logger)
    assert log.name == "bike_analyzer.test.delegate"
