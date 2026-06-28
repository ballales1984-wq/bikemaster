"""Tests for main entry point."""

from io import StringIO
from unittest.mock import patch

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
