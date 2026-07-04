"""Tests for google_health module."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.ingestion.google_health import (
    _child_text,
    _parse_tcx_time,
    _strip_ns,
    _summary_from_exercise,
    exchange_code_for_token,
    export_exercise_tcx,
    fetch_exercises,
    get_authorization_url,
    google_health_to_ride,
    google_health_to_rides,
    tcx_to_points,
)


class TestGetAuthorizationUrl:
    def test_returns_url(self):
        url = get_authorization_url("client123")
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")

    def test_contains_client_id(self):
        url = get_authorization_url("my_client_id")
        assert "client_id=my_client_id" in url

    def test_custom_redirect_uri(self):
        url = get_authorization_url("cid", redirect_uri="https://example.com/callback")
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in url

    def test_custom_state(self):
        url = get_authorization_url("cid", state="state123")
        assert "state=state123" in url

    def test_scope_present(self):
        url = get_authorization_url("cid")
        assert "scope=" in url
        assert "googlehealth.activity_and_fitness.readonly" in url
        assert "googlehealth.location.readonly" in url

    def test_response_type(self):
        url = get_authorization_url("cid")
        assert "response_type=code" in url

    def test_access_type_offline(self):
        url = get_authorization_url("cid")
        assert "access_type=offline" in url


class TestExchangeCodeForToken:
    @patch("requests.post")
    def test_exchanges_code(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "at_123", "refresh_token": "rt_123"}
        mock_post.return_value = mock_resp

        result = exchange_code_for_token("cid", "csecret", "code_abc", "https://cb")
        assert result["access_token"] == "at_123"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["data"]["grant_type"] == "authorization_code"
        assert call_kwargs["data"]["code"] == "code_abc"

    @patch("requests.post")
    def test_raises_on_http_error(self, mock_post):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("401")
        mock_post.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            exchange_code_for_token("cid", "csecret", "bad_code", "https://cb")


class TestFetchExercises:
    @patch("requests.get")
    def test_fetch_single_page(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"dataPoints": [{"name": "ex1", "displayName": "Ride 1"}]}
        mock_get.return_value = mock_resp

        result = fetch_exercises("token_abc", days=30)
        assert len(result) == 1
        assert result[0]["name"] == "ex1"

    @patch("requests.get")
    def test_fetch_paginated(self, mock_get):
        page1 = {"dataPoints": [{"name": "ex1"}], "nextPageToken": "next"}
        page2 = {"dataPoints": [{"name": "ex2"}], "nextPageToken": None}
        mock_get.side_effect = [MagicMock(json=MagicMock(return_value=p)) for p in (page1, page2)]

        result = fetch_exercises("token_abc", days=30)
        assert len(result) == 2
        assert result[1]["name"] == "ex2"

    @patch("requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"dataPoints": []}
        mock_get.return_value = mock_resp

        result = fetch_exercises("token_abc", days=7)
        assert result == []

    @patch("requests.get")
    def test_raises_on_forbidden(self, mock_get):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            fetch_exercises("token_abc", days=7)


class TestExportExerciseTcx:
    @patch("requests.get")
    def test_returns_tcx_data(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/xml"}
        mock_resp.text = "<TrainingCenterDatabase>...</TrainingCenterDatabase>"
        mock_get.return_value = mock_resp

        result = export_exercise_tcx("token_abc", "exercise_name")
        assert "TrainingCenterDatabase" in result

    @patch("requests.get")
    def test_json_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"tcxData": "<TCX>data</TCX>"}
        mock_get.return_value = mock_resp

        result = export_exercise_tcx("token_abc", "exercise_name")
        assert result == "<TCX>data</TCX>"

    @patch("requests.get")
    def test_request_failure(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("Network down")
        with pytest.raises(requests.ConnectionError):
            export_exercise_tcx("token_abc", "exercise_name")


class TestStripNs:
    def test_namespace_removed(self):
        assert _strip_ns("{http://ns}Tag") == "Tag"

    def test_no_namespace(self):
        assert _strip_ns("PlainTag") == "PlainTag"

    def test_empty_string(self):
        assert _strip_ns("") == ""


class TestChildText:
    def setup_method(self):
        self.root = ET.Element("parent")
        child = ET.SubElement(self.root, "child")
        child.text = "  value  "

    def test_found(self):
        result = _child_text(self.root, "child")
        assert result == "value"

    def test_not_found(self):
        result = _child_text(self.root, "missing")
        assert result is None

    def test_empty_text(self):
        child = ET.SubElement(self.root, "empty")
        child.text = "   "
        result = _child_text(self.root, "empty")
        assert result is None

    def test_none_text(self):
        child = ET.SubElement(self.root, "nonetext")
        child.text = None
        result = _child_text(self.root, "nonetext")
        assert result is None


class TestParseTcxTime:
    def test_valid_iso(self):
        result = _parse_tcx_time("2024-01-15T08:30:00Z")
        assert result == datetime(2024, 1, 15, 8, 30, 0, tzinfo=UTC)

    def test_none_input(self):
        assert _parse_tcx_time(None) is None

    def test_empty_string(self):
        assert _parse_tcx_time("") is None

    def test_invalid_format(self):
        assert _parse_tcx_time("not-a-date") is None


class TestTcxToPoints:
    TCX_SAMPLE = """<?xml version="1.0"?>
<TrainingCenterDatabase>
  <Activities>
    <Activity>
      <Lap>
        <Track>
          <Trackpoint>
            <Time>2024-01-15T08:00:00Z</Time>
            <Position>
              <LatitudeDegrees>45.0</LatitudeDegrees>
              <LongitudeDegrees>9.0</LongitudeDegrees>
            </Position>
            <AltitudeMeters>120.5</AltitudeMeters>
            <Value>145</Value>
            <Speed>5.0</Speed>
          </Trackpoint>
          <Trackpoint>
            <Time>2024-01-15T08:00:01Z</Time>
            <Position>
              <LatitudeDegrees>45.001</LatitudeDegrees>
              <LongitudeDegrees>9.001</LongitudeDegrees>
            </Position>
          </Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>"""

    def test_parses_points(self):
        points = tcx_to_points(self.TCX_SAMPLE)
        assert len(points) == 2
        assert points[0]["lat"] == 45.0
        assert points[0]["lon"] == 9.0
        assert points[0]["heart_rate"] == 145
        assert points[0]["speed"] == 18.0  # 5.0 * 3.6
        assert points[0]["altitude"] == 120.5

    def test_missing_optional_fields(self):
        points = tcx_to_points(self.TCX_SAMPLE)
        assert points[1]["heart_rate"] is None
        assert points[1]["speed"] is None

    def test_empty_content(self):
        assert tcx_to_points("") == []

    def test_none_content(self):
        assert tcx_to_points(None) == []

    def test_invalid_coords(self):
        tcx = """<?xml version="1.0"?>
<TrainingCenterDatabase>
  <Activities>
    <Activity>
      <Lap>
        <Track>
          <Trackpoint>
            <Time>2024-01-15T08:00:00Z</Time>
            <Position>
              <LatitudeDegrees>not-a-number</LatitudeDegrees>
              <LongitudeDegrees>9.0</LongitudeDegrees>
            </Position>
          </Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>"""
        points = tcx_to_points(tcx)
        assert len(points) == 0

    def test_speed_conversion(self):
        tcx = """<?xml version="1.0"?>
<TrainingCenterDatabase>
  <Activities>
    <Activity>
      <Lap>
        <Track>
          <Trackpoint>
            <Time>2024-01-15T08:00:00Z</Time>
            <Position>
              <LatitudeDegrees>45.0</LatitudeDegrees>
              <LongitudeDegrees>9.0</LongitudeDegrees>
            </Position>
            <Speed>10.0</Speed>
          </Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>"""
        points = tcx_to_points(tcx)
        assert points[0]["speed"] == 36.0


class TestSummaryFromExercise:
    def test_basic_exercise(self):
        exercise = {
            "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T09:00:00Z"},
            "displayName": "Morning Ride",
            "name": "ex_name_1",
            "metricsSummary": {
                "distanceMeters": 10000,
                "activeEnergy": 450,
                "averageSpeed": 3.0,
            },
        }
        result = _summary_from_exercise(exercise)
        assert result["date"] == "2024-01-15"
        assert result["duration_minutes"] == 60.0
        assert result["distance_km"] == 10.0
        assert result["external_source"] == "google_health"
        assert result["external_id"] == "ex_name_1"

    def test_custom_title(self):
        exercise = {
            "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T08:30:00Z"},
            "displayName": "Test",
        }
        result = _summary_from_exercise(exercise, title="My Custom Title")
        assert result["title"] == "My Custom Title"

    def test_missing_display_name(self):
        exercise = {
            "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T08:30:00Z"},
            "name": "ex_name",
        }
        result = _summary_from_exercise(exercise)
        assert result["title"] == "Uscita Google Health"

    def test_no_metrics(self):
        exercise = {
            "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T08:30:00Z"},
        }
        result = _summary_from_exercise(exercise)
        assert result["distance_km"] == 0
        assert result["calories"] == 0

    def test_no_interval(self):
        exercise = {}
        result = _summary_from_exercise(exercise)
        assert result["duration_minutes"] == 0
        assert result["distance_km"] == 0


class TestGoogleHealthToRides:
    @patch("bike_analyzer.backend.ingestion.google_health.fetch_exercises")
    @patch("bike_analyzer.backend.ingestion.google_health.export_exercise_tcx")
    def test_with_point_data(self, mock_tcx, mock_fetch):
        mock_fetch.return_value = [
            {
                "name": "ex1",
                "displayName": "Ride 1",
                "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T08:30:00Z"},
            }
        ]
        mock_tcx.return_value = """<?xml version="1.0"?>
<TrainingCenterDatabase>
  <Activities>
    <Activity>
      <Lap>
        <Track>
          <Trackpoint>
            <Time>2024-01-15T08:00:00Z</Time>
            <Position>
              <LatitudeDegrees>45.0</LatitudeDegrees>
              <LongitudeDegrees>9.0</LongitudeDegrees>
            </Position>
          </Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>"""

        with patch("bike_analyzer.backend.ingestion.google_health.points_to_ride") as mock_pt:
            mock_pt.return_value = {"title": "Ride 1", "distance_km": 5.0}
            result = google_health_to_rides("token_abc", athlete_id=1, days=7)
            assert len(result) == 1
            assert result[0]["athlete_id"] == 1

    @patch("bike_analyzer.backend.ingestion.google_health.fetch_exercises")
    def test_no_exercise_name(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T08:30:00Z"},
            }
        ]
        result = google_health_to_rides("token_abc", athlete_id=1, days=7)
        assert len(result) == 1
        assert result[0]["athlete_id"] == 1

    @patch("bike_analyzer.backend.ingestion.google_health.fetch_exercises")
    def test_fetch_returns_none(self, mock_fetch):
        mock_fetch.return_value = None
        with pytest.raises(TypeError):
            google_health_to_rides("token_abc", athlete_id=1, days=7)

    @patch("bike_analyzer.backend.ingestion.google_health.fetch_exercises")
    def test_empty_exercises(self, mock_fetch):
        mock_fetch.return_value = []
        result = google_health_to_rides("token_abc", athlete_id=1, days=7)
        assert result == []


class TestGoogleHealthToRide:
    def test_basic(self):
        exercises = [
            {
                "interval": {"startTime": "2024-01-15T08:00:00Z", "endTime": "2024-01-15T08:30:00Z"},
                "displayName": "Test Ride",
                "name": "ex1",
            }
        ]
        result = google_health_to_ride(exercises)
        assert len(result) == 1
        assert result[0]["date"] == "2024-01-15"
