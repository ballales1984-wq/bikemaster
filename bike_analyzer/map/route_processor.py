from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from bike_analyzer.map.gps_parser import GPSPoint, GPSRoute


EARTH_RADIUS_M = 6_371_000
PAUSE_SPEED_THRESHOLD_KM_H = 1.5
PAUSE_MIN_DURATION_MINUTES = 3


@dataclass
class Segment:
    start: GPSPoint
    end: GPSPoint
    distance_m: float
    duration_s: float
    avg_speed_km_h: float
    elevation_gain_m: float = 0.0
    elevation_loss_m: float = 0.0


@dataclass
class Pause:
    start: datetime
    end: datetime
    duration_s: float


@dataclass
class RouteStatistics:
    total_distance_m: float
    total_duration_s: float
    total_pause_duration_s: float
    avg_speed_km_h: float
    max_speed_km_h: float
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    segment_count: int
    pause_count: int


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def detect_pauses(points: List[GPSPoint]) -> List[Pause]:
    pauses: List[Pause] = []
    if len(points) < 2:
        return pauses

    pause_start: Optional[GPSPoint] = None

    for i in range(1, len(points)):
        prev_point = points[i - 1]
        curr_point = points[i]

        if curr_point.speed is not None and curr_point.speed < PAUSE_SPEED_THRESHOLD_KM_H:
            if pause_start is None:
                pause_start = prev_point
        else:
            if pause_start is not None:
                pause_end = prev_point
                duration = (pause_end.timestamp - pause_start.timestamp).total_seconds()
                if duration >= PAUSE_MIN_DURATION_MINUTES * 60 and pause_end.timestamp > pause_start.timestamp:
                    pauses.append(
                        Pause(
                            start=pause_start.timestamp,
                            end=pause_end.timestamp,
                            duration_s=duration,
                        )
                    )
                pause_start = None

    if pause_start is not None:
        last_point = points[-1]
        duration = (last_point.timestamp - pause_start.timestamp).total_seconds()
        if duration >= PAUSE_MIN_DURATION_MINUTES * 60 and last_point.timestamp > pause_start.timestamp:
            pauses.append(
                Pause(
                    start=pause_start.timestamp,
                    end=last_point.timestamp,
                    duration_s=duration,
                )
            )

    return pauses


def remove_outliers(points: List[GPSPoint], max_speed_km_h: float = 120.0) -> List[GPSPoint]:
    if len(points) < 3:
        return points[:]

    cleaned = [points[0]]

    for i in range(1, len(points) - 1):
        prev = cleaned[-1]
        curr = points[i]
        nxt = points[i + 1]

        dist_prev_curr = haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon)
        time_s = (curr.timestamp - prev.timestamp).total_seconds()
        if time_s <= 0:
            continue
        speed_km_h = (dist_prev_curr / time_s) * 3.6
        if speed_km_h > max_speed_km_h:
            continue
        cleaned.append(curr)

    if points[-1] != cleaned[-1]:
        dist = haversine_distance_m(cleaned[-1].lat, cleaned[-1].lon, points[-1].lat, points[-1].lon)
        time_s = (points[-1].timestamp - cleaned[-1].timestamp).total_seconds()
        if time_s > 0:
            speed_km_h = (dist / time_s) * 3.6
            if speed_km_h <= max_speed_km_h:
                cleaned.append(points[-1])

    return cleaned if len(cleaned) >= 2 else points[:2]


def build_segments(points: List[GPSPoint]) -> List[Segment]:
    segments: List[Segment] = []
    if len(points) < 2:
        return segments

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]

        dist_m = haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon)
        duration_s = (curr.timestamp - prev.timestamp).total_seconds()

        if duration_s <= 0:
            continue

        avg_speed = (dist_m / duration_s) * 3.6
        elev_gain, elev_loss = _elevation_delta(prev.altitude, curr.altitude)

        segments.append(
            Segment(
                start=prev,
                end=curr,
                distance_m=dist_m,
                duration_s=duration_s,
                avg_speed_km_h=avg_speed,
                elevation_gain_m=elev_gain,
                elevation_loss_m=elev_loss,
            )
        )

    return segments


def _elevation_delta(alt_from: Optional[float], alt_to: Optional[float]) -> Tuple[float, float]:
    if alt_from is None or alt_to is None:
        return 0.0, 0.0
    delta = alt_to - alt_from
    if delta > 0:
        return delta, 0.0
    return 0.0, abs(delta)


def compute_statistics(points: List[GPSPoint]) -> RouteStatistics:
    segments = build_segments(points)
    pauses = detect_pauses(points)

    total_distance_m = sum(s.distance_m for s in segments)
    total_duration_s = segments[-1].end.timestamp.timestamp() - segments[0].start.timestamp.timestamp() if segments else 0.0
    total_pause_duration_s = sum(p.duration_s for p in pauses)

    moving_duration_s = total_duration_s - total_pause_duration_s
    avg_speed = (total_distance_m / moving_duration_s) * 3.6 if moving_duration_s > 0 else 0.0
    max_speed = max((s.avg_speed_km_h for s in segments), default=0.0)
    total_elev_gain = sum(s.elevation_gain_m for s in segments)
    total_elev_loss = sum(s.elevation_loss_m for s in segments)

    return RouteStatistics(
        total_distance_m=total_distance_m,
        total_duration_s=total_duration_s,
        total_pause_duration_s=total_pause_duration_s,
        avg_speed_km_h=avg_speed,
        max_speed_km_h=max_speed,
        total_elevation_gain_m=total_elev_gain,
        total_elevation_loss_m=total_elev_loss,
        segment_count=len(segments),
        pause_count=len(pauses),
    )


def process_route(route: GPSRoute, max_speed_km_h: float = 120.0) -> Tuple[List[GPSPoint], RouteStatistics]:
    route.sort_by_time()
    cleaned_points = remove_outliers(route.points, max_speed_km_h=max_speed_km_h)
    stats = compute_statistics(cleaned_points)
    return cleaned_points, stats
