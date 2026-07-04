"""Tests for frontend/dashboard module."""

import os
import tempfile

from bike_analyzer.frontend.dashboard import DASHBOARD_HTML, generate_dashboard_html


class TestDashboardHtml:
    def test_html_contains_title(self):
        assert "BikeMaster" in DASHBOARD_HTML

    def test_html_contains_stats_section(self):
        assert 'id="stats"' in DASHBOARD_HTML

    def test_html_contains_weather_section(self):
        assert "weather-section" in DASHBOARD_HTML

    def test_html_contains_rides_list(self):
        assert "rides-list" in DASHBOARD_HTML

    def test_html_contains_load_rides(self):
        assert "loadRides" in DASHBOARD_HTML

    def test_html_contains_fetch_weather(self):
        assert "fetchWeather" in DASHBOARD_HTML

    def test_html_contains_delete_ride(self):
        assert "deleteRide" in DASHBOARD_HTML

    def test_html_is_string(self):
        assert isinstance(DASHBOARD_HTML, str)
        assert len(DASHBOARD_HTML) > 1000

    def test_html_has_doctype(self):
        assert DASHBOARD_HTML.startswith("<!DOCTYPE html>")


class TestGenerateDashboardHtml:
    def test_generates_file(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            tmp_path = f.name
        try:
            result = generate_dashboard_html(tmp_path)
            assert result == tmp_path
            assert os.path.exists(tmp_path)
            with open(tmp_path, encoding="utf-8") as f:
                content = f.read()
            assert "BikeMaster" in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_default_path(self):
        result = generate_dashboard_html()
        assert result == "dashboard.html"
        assert os.path.exists("dashboard.html")
        with open("dashboard.html", encoding="utf-8") as f:
            content = f.read()
        assert "BikeMaster" in content
        os.unlink("dashboard.html")

    def test_returns_path(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            tmp_path = f.name
        try:
            result = generate_dashboard_html(tmp_path)
            assert result == tmp_path
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
