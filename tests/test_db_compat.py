"""Tests for db/api_compat module."""

from unittest.mock import MagicMock

from bike_analyzer.backend.db.api_compat import get_athlete_by_query


class TestGetAthleteByQuery:
    def test_empty_query_returns_none(self):
        result = get_athlete_by_query(MagicMock())
        assert result is None

    def test_name_query_calls_module(self):
        mock_db = MagicMock()
        mock_db.get_athlete_by_name.return_value = {"id": 1, "name": "Test"}
        result = get_athlete_by_query(mock_db, name="Test")
        mock_db.get_athlete_by_name.assert_called_once_with("Test")
        assert result == {"id": 1, "name": "Test"}

    def test_name_query_with_none(self):
        mock_db = MagicMock()
        result = get_athlete_by_query(mock_db, name=None)
        assert result is None

    def test_unknown_query_key_returns_none(self):
        mock_db = MagicMock()
        result = get_athlete_by_query(mock_db, unknown_key="value")
        assert result is None

    def test_name_converted_to_string(self):
        mock_db = MagicMock()
        mock_db.get_athlete_by_name.return_value = {"id": 1}
        result = get_athlete_by_query(mock_db, name=123)
        mock_db.get_athlete_by_name.assert_called_once_with("123")
