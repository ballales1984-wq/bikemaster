"""Automatic segment detection for climbs and notable routes."""
from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass
from ..models.models import GPSPoint, Segment, haversine_distance_m


@dataclass
class ClimbSegment:
    start_idx: int
    end_idx: int
    distance_m: float
    elevation_gain_m: float
    avg_grade_percent: float
    category: str  # "hc", "cat1", "cat2", "cat3", "cat4"
    start_point: GPSPoint
    end_point: GPSPoint


# Categorization thresholds (based on gradient * distance)
CLIMB_CATEGORIES = {
    "hc": (100000, 20.0),   # HC: >10km o >20% media
    "cat1": (80000, 15.0),  # Cat1: >8km o >15%
    "cat2": (40000, 10.0),  # Cat2: >4km o >10%
    "cat3": (20000, 6.0),   # Cat3: >2km o >6%
    "cat4": (5000, 3.0),    # Cat4: >500m o >3%
}


def calculate_grade_percent(elev_gain_m: float, distance_m: float) -> float:
    """Calculate average grade percentage."""
    if distance_m <= 0:
        return 0.0
    return (elev_gain_m / distance_m) * 100.0


def categorize_climb(grade: float, distance_m: float) -> str:
    """Categorize climb based on difficulty."""
    for cat, (dist_thresh, grade_thresh) in CLIMB_CATEGORIES.items():
        if distance_m >= dist_thresh or grade >= grade_thresh:
            return cat
    return "unclassified"


def detect_climb_segments(points: List[GPSPoint], min_distance_m: float = 500, min_elevation_m: float = 30) -> List[ClimbSegment]:
    """Detect climb segments from GPS points.
    
    Args:
        points: List of GPS points sorted by timestamp
        min_distance_m: Minimum segment length (default 500m)
        min_elevation_m: Minimum elevation gain (default 30m)
    
    Returns:
        List of detected climb segments with categorization
    """
    if len(points) < 3:
        return []
    
    climbs: List[ClimbSegment] = []
    in_climb = False
    climb_start = 0
    climb_dist = 0.0
    climb_elev = 0.0
    prev_idx = 0
    
    for i in range(1, len(points)):
        prev = points[prev_idx]
        curr = points[i]
        
        dist = haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon)
        elev_gain = 0.0
        
        if prev.altitude and curr.altitude and curr.altitude > prev.altitude:
            elev_gain = curr.altitude - prev.altitude
        
        climb_dist += dist
        climb_elev += elev_gain
        
        if elev_gain > 0 and not in_climb:
            in_climb = True
            climb_start = prev_idx
            climb_dist = 0.0
            climb_elev = 0.0
        elif elev_gain == 0 and in_climb:
            if climb_dist >= min_distance_m and climb_elev >= min_elevation_m:
                grade = calculate_grade_percent(climb_elev, climb_dist)
                if grade > 0:
                    climbs.append(ClimbSegment(
                        start_idx=climb_start,
                        end_idx=i - 1,
                        distance_m=climb_dist,
                        elevation_gain_m=climb_elev,
                        avg_grade_percent=grade,
                        category=categorize_climb(grade, climb_dist),
                        start_point=points[climb_start],
                        end_point=points[i - 1]
                    ))
            in_climb = False
        
        prev_idx = i
    
    if in_climb and climb_dist >= min_distance_m and climb_elev >= min_elevation_m:
        grade = calculate_grade_percent(climb_elev, climb_dist)
        climbs.append(ClimbSegment(
            start_idx=climb_start,
            end_idx=len(points) - 1,
            distance_m=climb_dist,
            elevation_gain_m=climb_elev,
            avg_grade_percent=grade,
            category=categorize_climb(grade, climb_dist),
            start_point=points[climb_start],
            end_point=points[-1]
        ))
    
    return climbs


def detect_all_segments(points: List[GPSPoint], min_length_m: float = 1000) -> List[Segment]:
    """Detect all significant segments (not just climbs).
    
    Args:
        points: GPS points
        min_length_m: Minimum segment length (default 1km)
    
    Returns:
        List of segments >= min_length_m
    """
    if len(points) < 2:
        return []
    
    segments: List[Segment] = []
    segment_start = 0
    accum_dist = 0.0
    accum_elev_gain = 0.0
    accum_elev_loss = 0.0
    accum_speed = 0.0
    point_count = 0
    
    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        
        dist = haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon)
        duration = (curr.timestamp - prev.timestamp).total_seconds()
        if duration <= 0:
            continue
        
        speed = (dist / duration) * 3.6
        accum_dist += dist
        accum_speed += speed
        point_count += 1
        
        if prev.altitude and curr.altitude:
            if curr.altitude > prev.altitude:
                accum_elev_gain += curr.altitude - prev.altitude
            else:
                accum_elev_loss += prev.altitude - curr.altitude
        
        if accum_dist >= min_length_m:
            avg_speed = accum_speed / point_count if point_count > 0 else 0
            segments.append(Segment(
                start=points[segment_start],
                end=curr,
                distance_m=accum_dist,
                duration_s=sum(
                    (points[j+1].timestamp - points[j].timestamp).total_seconds()
                    for j in range(segment_start, i)
                    if j + 1 < len(points)
                ),
                avg_speed_km_h=avg_speed,
                elevation_gain_m=accum_elev_gain,
                elevation_loss_m=accum_elev_loss
            ))
            segment_start = i
            accum_dist = 0.0
            accum_elev_gain = 0.0
            accum_elev_loss = 0.0
            accum_speed = 0.0
            point_count = 0
    
    return segments


def segment_to_dict(segment: ClimbSegment) -> dict:
    """Convert climb segment to serializable dict."""
    return {
        "start_idx": segment.start_idx,
        "end_idx": segment.end_idx,
        "distance_km": round(segment.distance_m / 1000, 2),
        "elevation_gain_m": round(segment.elevation_gain_m, 1),
        "avg_grade_percent": round(segment.avg_grade_percent, 1),
        "category": segment.category,
        "start_lat": segment.start_point.lat,
        "start_lon": segment.start_point.lon,
        "end_lat": segment.end_point.lat,
        "end_lon": segment.end_point.lon
    }


__all__ = [
    "detect_climb_segments",
    "detect_all_segments",
    "ClimbSegment",
    "segment_to_dict"
]