"""Test database ORM."""
from bike_analyzer.backend.db.orm import init_orm, get_session, RideORM, AthleteORM, orm_to_dict
from bike_analyzer.backend.models.models import Ride

def test_orm_init():
    init_orm()
    assert True

def test_create_ride():
    session = get_session()
    ride = RideORM(date="2024-06-01", distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0)
    session.add(ride)
    session.commit()
    assert ride.id is not None
    session.delete(ride)
    session.commit()
    session.close()

def test_create_athlete():
    session = get_session()
    athlete = AthleteORM(name="Test Athlete", age=30, weight_kg=70.0)
    session.add(athlete)
    session.commit()
    assert athlete.id is not None
    session.delete(athlete)
    session.commit()
    session.close()

def test_orm_to_dict():
    ride = RideORM(date="2024-06-01", distance_km=25.0)
    d = orm_to_dict(ride)
    assert d["date"] == "2024-06-01"