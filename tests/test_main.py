"""Tests for main entry point."""

from unittest.mock import patch

import pytest

from bike_analyzer.main import main


class TestMain:
    def test_main_runs(self):
        with patch("bike_analyzer.main.print") as mock_print:
            main()
            assert mock_print.called

    def test_main_creates_rides(self):
        with patch("bike_analyzer.main.print") as mock_print:
            main()
            assert mock_print.call_count >= 1
            printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            assert "BikeMaster" in printed
            assert "Rides:" in printed


def test_bike_analyzer_version():
    import bike_analyzer

    assert bike_analyzer.__version__ == "0.1.0"


def test_bike_analyzer_getattr_valid():
    import bike_analyzer

    assert hasattr(bike_analyzer, "Ride")
    assert hasattr(bike_analyzer, "GPSPoint")
    assert hasattr(bike_analyzer, "calculate_summary")


def test_bike_analyzer_getattr_invalid():
    import bike_analyzer

    with pytest.raises(AttributeError):
        _ = bike_analyzer.NonExistent


def test_bike_analyzer_all_exports():
    import bike_analyzer

    # __all__ is a set of strings, check it contains expected exports
    assert "__version__" in bike_analyzer.__all__
    assert "Ride" in bike_analyzer.__all__
    assert "GPSPoint" in bike_analyzer.__all__
