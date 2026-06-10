"""Test coverage for main entry point."""

from bike_analyzer.main import main


def test_main_output(capsys):
    main()
    captured = capsys.readouterr()
    assert "BikeMaster" in captured.out
    assert "Rides:" in captured.out
    assert "Distance:" in captured.out
