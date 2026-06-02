from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from bike_analyzer.map.gps_parser import GPSPoint, GPSRoute
from bike_analyzer.map.route_processor import (
    Pause,
    RouteStatistics,
    Segment,
    build_segments,
    detect_pauses,
    process_route,
)


@dataclass
class ProcessedRoute:
    points: List[GPSPoint]
    segments: List[Segment]
    statistics: RouteStatistics
    pauses: List[Pause]


@dataclass
class SpeedSegment:
    points: List[Tuple[float, float]]
    avg_speed_km_h: float


def build_segment_speeds(points: List[GPSPoint]) -> List[SpeedSegment]:
    segments = build_segments(points)
    result: List[SpeedSegment] = []
    for seg in segments:
        result.append(
            SpeedSegment(
                points=[(seg.start.lat, seg.start.lon), (seg.end.lat, seg.end.lon)],
                avg_speed_km_h=seg.avg_speed_km_h,
            )
        )
    return result


def extract_route_coordinates(points: List[GPSPoint]) -> List[Tuple[float, float]]:
    return [(p.lat, p.lon) for p in points]


def build_processed_route(route: GPSRoute) -> ProcessedRoute:
    cleaned_points, stats = process_route(route)
    segments = build_segments(cleaned_points)
    pauses = detect_pauses(cleaned_points)

    return ProcessedRoute(
        points=cleaned_points,
        segments=segments,
        statistics=stats,
        pauses=pauses,
    )
