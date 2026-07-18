"""GPS data processing and cleaning module."""

from __future__ import annotations

from datetime import datetime

from ..models.models import (
    GPSPoint,
    Pause,
    RouteStatistics,
    Segment,
    haversine_distance_m,
)

PAUSE_SPEED_THRESHOLD_KM_H = 1.5
PAUSE_MIN_DURATION_MINUTES = 3
ACCEL_THRESHOLD_KM_H_S = 2.0
DECEL_THRESHOLD_KM_H_S = -2.0


def validate_coordinate(lat: float, lon: float) -> bool:
    """Valida latitudine [-90,90] e longitudine [-180,180] come numeri finiti."""
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    if lat < -90 or lat > 90:
        return False
    return not (lon < -180 or lon > 180)


def validate_gps_point(point: GPSPoint) -> bool:
    return validate_coordinate(point.lat, point.lon) and isinstance(point.timestamp, datetime)


def detect_pauses(points: list[GPSPoint]) -> list[Pause]:
    """Rileva le pause nella traccia: segmenti con speed < 1.5 km/h continui.

    Un punto è "pausa" se la sua velocità scende sotto la soglia; quando la
    velocità risale, se la durata accumulata >= 3 minuti viene emesso un oggetto
    ``Pause`` (start/end/duration_s). Gestisce una sola pausa aperta per volta.
    """
    pauses: list[Pause] = []
    if len(points) < 2:
        return pauses
    pause_start: GPSPoint | None = None
    for i in range(1, len(points)):
        curr = points[i]
        if curr.speed is not None and curr.speed < PAUSE_SPEED_THRESHOLD_KM_H:
            if pause_start is None:
                pause_start = points[i - 1]
        else:
            if pause_start is not None:
                pause_end = points[i - 1]
                duration = (pause_end.timestamp - pause_start.timestamp).total_seconds()
                if duration >= PAUSE_MIN_DURATION_MINUTES * 60:
                    pauses.append(
                        Pause(
                            start=pause_start.timestamp,
                            end=pause_end.timestamp,
                            duration_s=duration,
                        )
                    )
                pause_start = None
    return pauses


def detect_accelerations(points: list[GPSPoint]) -> list[tuple[int, float]]:
    accels = []
    if len(points) < 2:
        return accels
    for i in range(1, len(points)):
        if points[i - 1].speed is not None and points[i].speed is not None:
            delta = points[i].speed - points[i - 1].speed
            if delta >= ACCEL_THRESHOLD_KM_H_S:
                accels.append((i, delta))
    return accels


def detect_decelerations(points: list[GPSPoint]) -> list[tuple[int, float]]:
    decels = []
    if len(points) < 2:
        return decels
    for i in range(1, len(points)):
        if points[i - 1].speed is not None and points[i].speed is not None:
            delta = points[i].speed - points[i - 1].speed
            if delta <= DECEL_THRESHOLD_KM_H_S:
                decels.append((i, delta))
    return decels


def remove_outliers(points: list[GPSPoint], max_speed_km_h: float = 120.0) -> list[GPSPoint]:
    """Rimuove i point GPS che implicherebbero una velocità implausibile.

    Calcola la velocità istantanea tra punti consecutivi via haversine/delta-t e
    scarta i punti che la superano (default 120 km/h, tipico di errori GPS).
    Mantiene sempre il primo e l'ultimo punto. Se pulendo restano <2 punti,
    ritorna i primi due dell'originale per non rompere i consumatori a valle.
    """
    if len(points) < 3:
        return points[:]
    cleaned = [points[0]]
    for i in range(1, len(points) - 1):
        prev, curr = cleaned[-1], points[i]
        time_s = (curr.timestamp - prev.timestamp).total_seconds()
        if time_s <= 0:
            continue
        speed = (haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon) / time_s) * 3.6
        if speed <= max_speed_km_h:
            cleaned.append(curr)
    if points[-1] != cleaned[-1]:
        last = points[-1]
        time_s = (last.timestamp - cleaned[-1].timestamp).total_seconds()
        if time_s > 0:
            speed = (haversine_distance_m(cleaned[-1].lat, cleaned[-1].lon, last.lat, last.lon) / time_s) * 3.6
            if speed <= max_speed_km_h:
                cleaned.append(last)
    return cleaned if len(cleaned) >= 2 else points[:2]


def _elevation_delta(alt_from: float | None, alt_to: float | None) -> tuple[float, float]:
    if alt_from is None or alt_to is None:
        return 0.0, 0.0
    return (alt_to - alt_from, 0.0) if alt_to > alt_from else (0.0, abs(alt_to - alt_from))


def build_segments(points: list[GPSPoint]) -> list[Segment]:
    """Costruisce i segmenti punto-a-punto della rotta.

    Per ogni coppia consecutiva calcola distanza (haversine), durata, velocità
    media e variazione di quota (gain/loss), saltando i passi con delta-t <= 0.
    """
    segments: list[Segment] = []
    for i in range(1, len(points)):
        prev, curr = points[i - 1], points[i]
        dist_m = haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon)
        duration_s = (curr.timestamp - prev.timestamp).total_seconds()
        if duration_s <= 0:
            continue
        elev_gain, elev_loss = _elevation_delta(prev.altitude, curr.altitude)
        segments.append(
            Segment(
                start=prev,
                end=curr,
                distance_m=dist_m,
                duration_s=duration_s,
                avg_speed_km_h=(dist_m / duration_s) * 3.6,
                elevation_gain_m=elev_gain,
                elevation_loss_m=elev_loss,
            )
        )
    return segments


def compute_statistics(points: list[GPSPoint]) -> RouteStatistics:
    """Aggrega statistiche di rotta: distanza, durata, pause, velocità, dislivello.

    La durata totale è la finestra tra primo e ultimo segmento; il tempo in
    movimento sottrae le pause rilevate. La velocità media usa il tempo in
    movimento (non il tempo totale) per essere realistica.
    """
    segments = build_segments(points)
    pauses = detect_pauses(points)
    total_distance_m = sum(s.distance_m for s in segments)
    total_duration_s = (
        (segments[-1].end.timestamp.timestamp() - segments[0].start.timestamp.timestamp()) if segments else 0.0
    )
    moving_s = total_duration_s - sum(p.duration_s for p in pauses)
    return RouteStatistics(
        total_distance_m=total_distance_m,
        total_duration_s=total_duration_s,
        total_pause_duration_s=sum(p.duration_s for p in pauses),
        avg_speed_km_h=(total_distance_m / moving_s) * 3.6 if moving_s > 0 else 0.0,
        max_speed_km_h=max((s.avg_speed_km_h for s in segments), default=0.0),
        total_elevation_gain_m=sum(s.elevation_gain_m for s in segments),
        total_elevation_loss_m=sum(s.elevation_loss_m for s in segments),
        segment_count=len(segments),
        pause_count=len(pauses),
    )


def process_route(points: list[GPSPoint], max_speed_km_h: float = 120.0) -> tuple[list[GPSPoint], RouteStatistics]:
    """Pipeline completa di una rotta: ordina per timestamp, rimuove outlier, calcola statistiche."""
    points = sorted(points, key=lambda p: p.timestamp)
    cleaned = remove_outliers(points, max_speed_km_h)
    return cleaned, compute_statistics(cleaned)
