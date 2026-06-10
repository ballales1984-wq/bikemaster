"""Test coverage for frontend dashboard generator."""

import os
import tempfile

from bike_analyzer.frontend.dashboard import DASHBOARD_HTML, generate_dashboard_html


def test_dashboard_html_constant():
    assert DASHBOARD_HTML is not None
    assert "<!DOCTYPE html>" in DASHBOARD_HTML
    assert "BikeMaster" in DASHBOARD_HTML
    assert "cycling" in DASHBOARD_HTML.lower()


def test_generate_dashboard_html():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test_dashboard.html")
        result = generate_dashboard_html(output_path)
        assert result == output_path
        assert os.path.exists(output_path)
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "BikeMaster" in content


def test_generate_dashboard_html_default_path():
    result = generate_dashboard_html("dashboard_test_default.html")
    assert result == "dashboard_test_default.html"
    assert os.path.exists("dashboard_test_default.html")
    os.remove("dashboard_test_default.html")


def test_frontend_main_block(capsys):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "bike_analyzer.frontend.dashboard"], capture_output=True, text=True
    )
    assert "Dashboard generated" in result.stdout
