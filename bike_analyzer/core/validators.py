"""Business validators for BikeMaster.

Provides functions that validate raw input data (dicts, external API responses,
file imports) using the Pydantic models from validation.py, then convert them
to core domain dataclass instances.
"""

from __future__ import annotations

from datetime import date

from pydantic import ValidationError

from bike_analyzer.core.models import AthleteProfile as AthleteProfileDataclass
from bike_analyzer.core.models import GPSPoint as GPSPointDataclass
from bike_analyzer.core.models import Ride as RideDataclass
from bike_analyzer.core.validation import (
    ValidatedAthleteProfile,
    ValidatedGPSPoint,
    ValidatedRide,
)


class BusinessValidationError(Exception):
    """Errore di validazione business rule per dati di ingresso non conformi."""

    pass


def validate_ride_for_analysis(ride_data: dict) -> RideDataclass:
    """Valida e converte dati ride per analisi (controlli Pydantic + regole business)."""
    try:
        validated = ValidatedRide.model_validate(ride_data)
    except ValidationError as exc:
        raise BusinessValidationError({"message": "Dati ride non validi", "errors": exc.errors()}) from exc
    return _to_domain_ride(validated)


def validate_ride_for_import(ride_data: dict) -> RideDataclass:
    """Valida e converte dati ride per import (controlli Pydantic + regole business)."""
    try:
        validated = ValidatedRide.model_validate(ride_data)
    except ValidationError as exc:
        raise BusinessValidationError({"message": "Dati ride import non validi", "errors": exc.errors()}) from exc
    return _to_domain_ride(validated)


def validate_gps_points(points_data: list[dict]) -> list[GPSPointDataclass]:
    """Valida lista di punti GPS e converte in domain dataclass."""
    if len(points_data) < 2:
        raise BusinessValidationError("Servono almeno 2 punti GPS per una ride valida")
    validated_points = []
    errors = []
    for i, p in enumerate(points_data):
        try:
            vp = ValidatedGPSPoint.model_validate(p)
            validated_points.append(_to_domain_gps_point(vp))
        except ValidationError as exc:
            errors.append({"index": i, "errors": exc.errors()})
    if errors:
        raise BusinessValidationError({"message": "Punti GPS non validi", "errors": errors})
    return validated_points


def validate_athlete_profile(data: dict) -> AthleteProfileDataclass:
    """Valida e converte dati profilo atleta."""
    try:
        validated = ValidatedAthleteProfile.model_validate(data)
    except ValidationError as exc:
        raise BusinessValidationError({"message": "Dati profilo atleta non validi", "errors": exc.errors()}) from exc
    return _to_domain_athlete(validated)


def validate_athlete_profile_partial(data: dict) -> AthleteProfileDataclass:
    """Valida profilo atleta senza richiedere campi obbligatori (partial update)."""
    validated = ValidatedAthleteProfile.model_validate(data)
    return _to_domain_athlete(validated)


def _to_domain_gps_point(vp: ValidatedGPSPoint) -> GPSPointDataclass:
    """Converte ValidatedGPSPoint (Pydantic) in GPSPointDataclass (domain)."""
    return GPSPointDataclass(
        lat=vp.lat,
        lon=vp.lon,
        timestamp=vp.timestamp,
        altitude=vp.altitude,
        speed=vp.speed,
        power=vp.power,
        heart_rate=vp.heart_rate,
        cadence=vp.cadence,
    )


def _to_domain_ride(vr: ValidatedRide) -> RideDataclass:
    """Converte ValidatedRide (Pydantic) in RideDataclass (domain)."""
    gps_points = [_to_domain_gps_point(p) for p in vr.gps_points]
    ride = RideDataclass(
        athlete_id=vr.athlete_id,
        date=vr.date.isoformat() if isinstance(vr.date, date) else str(vr.date),
        distance_km=vr.distance_km,
        duration_minutes=vr.duration_minutes,
        avg_speed_kmh=vr.avg_speed_kmh,
        elevation_gain_m=vr.elevation_gain_m,
        calories=vr.calories,
        gps_points=gps_points if gps_points else None,
        title=vr.title,
        external_source=vr.external_source,
        external_id=vr.external_id,
    )
    return ride


def _to_domain_athlete(va: ValidatedAthleteProfile) -> AthleteProfileDataclass:
    """Converte ValidatedAthleteProfile (Pydantic) in AthleteProfileDataclass (domain)."""
    return AthleteProfileDataclass(
        id=va.id,
        name=va.name,
        age=va.age,
        weight_kg=va.weight_kg,
        height_cm=va.height_cm,
        ftp_watts=va.ftp_watts,
        experience_level=va.experience_level,
    )
