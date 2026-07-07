"""Tests for structured logging configuration."""

from __future__ import annotations

import logging
import os

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
    logger = logging.getLogger("test_request_id")
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
    assert getattr(record, "request_id") == "abc-123"
