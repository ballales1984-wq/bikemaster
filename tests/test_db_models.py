"""Tests for SQLAlchemy ORM models."""
import pytest
from datetime import datetime, UTC
from bike_analyzer.backend.db.models import (
    Base,
    AthleteModel,
    RideModel,
    MetricModel,
    StravaTokenModel,
    GarminTokenModel,
    CalendarEventModel,
    KnowledgeChunkModel,
    ChatMessageModel,
)


def test_base_has_metadata():
    assert hasattr(Base, 'metadata')


def test_athlete_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(AthleteModel)
    columns = [c.key for c in mapper.columns]
    assert 'id' in columns
    assert 'name' in columns
    assert 'weight_kg' in columns
    assert 'experience_level' in columns


def test_athlete_model_table_name():
    assert AthleteModel.__tablename__ == "athletes"


def test_athlete_model_indexes():
    from sqlalchemy import inspect
    mapper = inspect(AthleteModel)
    table_args = AthleteModel.__table_args__
    index_names = []
    for arg in table_args:
        if hasattr(arg, 'name'):
            index_names.append(arg.name)
    assert 'ix_athletes_experience_level' in index_names
    assert 'ix_athletes_name' in index_names


def test_ride_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(RideModel)
    columns = [c.key for c in mapper.columns]
    assert 'id' in columns
    assert 'date' in columns
    assert 'distance_km' in columns
    assert 'external_source' in columns
    assert 'external_id' in columns


def test_ride_model_table_name():
    assert RideModel.__tablename__ == "rides"


def test_ride_model_indexes():
    table_args = RideModel.__table_args__
    combined = str(table_args)
    assert 'ix_rides_athlete_date' in combined
    assert 'ix_rides_distance' in combined
    assert 'ix_rides_elevation' in combined
    assert 'uq_rides_external_identity' in combined


def test_metric_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(MetricModel)
    columns = [c.key for c in mapper.columns]
    assert 'athlete_id' in columns
    assert 'metric_type' in columns
    assert 'value' in columns


def test_metric_model_table_name():
    assert MetricModel.__tablename__ == "metrics"


def test_strava_token_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(StravaTokenModel)
    columns = [c.key for c in mapper.columns]
    assert 'access_token' in columns
    assert 'refresh_token' in columns
    assert 'athlete_id' in columns


def test_strava_token_model_table_name():
    assert StravaTokenModel.__tablename__ == "strava_tokens"


def test_garmin_token_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(GarminTokenModel)
    columns = [c.key for c in mapper.columns]
    assert 'access_token' in columns
    assert 'athlete_id' in columns


def test_garmin_token_model_table_name():
    assert GarminTokenModel.__tablename__ == "garmin_tokens"


def test_calendar_event_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(CalendarEventModel)
    columns = [c.key for c in mapper.columns]
    assert 'title' in columns
    assert 'event_type' in columns
    assert 'completed' in columns


def test_calendar_event_model_table_name():
    assert CalendarEventModel.__tablename__ == "calendar_events"


def test_all_models_inherited_from_base():
    for model in [AthleteModel, RideModel, MetricModel, StravaTokenModel, GarminTokenModel, CalendarEventModel, KnowledgeChunkModel, ChatMessageModel]:
        assert issubclass(model, Base)


def test_knowledge_chunk_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(KnowledgeChunkModel)
    columns = [c.key for c in mapper.columns]
    assert "id" in columns
    assert "topic" in columns
    assert "chunk_id" in columns
    assert "text" in columns
    assert "embedding" in columns


def test_knowledge_chunk_model_table_name():
    assert KnowledgeChunkModel.__tablename__ == "knowledge_chunks"


def test_chat_message_model_columns():
    from sqlalchemy import inspect
    mapper = inspect(ChatMessageModel)
    columns = [c.key for c in mapper.columns]
    assert "id" in columns
    assert "athlete_id" in columns
    assert "role" in columns
    assert "content" in columns


def test_chat_message_model_table_name():
    assert ChatMessageModel.__tablename__ == "chat_messages"