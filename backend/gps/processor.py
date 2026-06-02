"""GPS cleaning, outlier removal, and distance/speed calculations"""

from datetime import datetime
from typing import Optional

import numpy as np
from scipy.spatial.distance import cdist
from scipy.interpolate import CubicSpline

EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Vectorized haversine distance in meters"""
    d_lat = np.radians(lat2 - lat1)
    d_lon = np.radians(lon2 - lon1)
    a = np.sin(d_lat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(d_lon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_M * c


def remove_stationary_points(lats: np.ndarray, lons: np.ndarray, timestamps: np.ndarray,
                              min_speed_ms: float = 0.5, window_seconds: float = 5.0) -> np.ndarray:
    """Remove points where the user appears stationary (GPS drift)"""
    if len(lats) < 3:
        return np.arange(len(lats))

    d = haversine_m(lats[:-1], lons[:-1], lats[1:], lons[1:])
    dt = np.diff(timestamps).astype("timedelta64[s]").astype(float)
    dt = np.maximum(dt, 0.1)
    speed = d / dt

    moving = speed >= min_speed_ms

    keep = np.zeros(len(lats), dtype=bool)
    keep[0] = True
    keep[-1] = True
    keep[1:-1] = moving

    return np.where(keep)[0]


def remove_jumps(lats: np.ndarray, lons: np.ndarray, max_jump_m: float = 500.0) -> np.ndarray:
    """Remove GPS jumps (points that are unrealistically far from neighbors)"""
    if len(lats) < 3:
        return np.arange(len(lats))

    d = haversine_m(lats[:-1], lons[:-1], lats[1:], lons[1:])
    bad_fwd = d > max_jump_m
    bad_rev = np.empty_like(bad_fwd)
    bad_rev[:-1] = bad_fwd[1:]
    bad_rev[-1] = False

    keep = ~(bad_fwd | bad_rev)
    keep[0] = True
    keep[-1] = True
    return np.where(keep)[0]


def remove_duplicates(lats: np.ndarray, lons: np.ndarray,
                       tolerance_m: float = 2.0) -> np.ndarray:
    """Remove near-duplicate GPS points"""
    if len(lats) < 2:
        return np.arange(len(lats))

    d = haversine_m(lats[:-1], lons[:-1], lats[1:], lons[1:])
    keep = d > tolerance_m
    keep = np.insert(keep, 0, True)
    keep[-1] = True
    return np.where(keep)[0]


def compute_segment_distances(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Compute distance between consecutive points in meters. Returns array of len-1."""
    return haversine_m(lats[:-1], lons[:-1], lats[1:], lons[1:])


def compute_speeds(distances_m: np.ndarray, dt_seconds: np.ndarray) -> np.ndarray:
    """Compute speed in km/h between consecutive points"""
    dt = np.maximum(dt_seconds, 0.1)
    speed_ms = distances_m / dt
    return speed_ms * 3.6


def compute_elevation_gain_loss(elevations: np.ndarray) -> tuple[float, float]:
    """Compute total elevation gain and loss in meters"""
    diffs = np.diff(elevations)
    gain = float(np.sum(diffs[diffs > 0]))
    loss = float(np.sum(-diffs[diffs < 0]))
    return gain, loss


def interpolate_gps(lats: np.ndarray, lons: np.ndarray, timestamps: np.ndarray,
                     target_interval_seconds: float = 5.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Interpolate GPS points to a regular time interval.
    Returns (lats, lons, timestamps) arrays.
    """
    if len(lats) < 2:
        return lats, lons, timestamps

    t_sec = timestamps.astype("datetime64[s]").astype(float)

    cs_lat = CubicSpline(t_sec, lats)
    cs_lon = CubicSpline(t_sec, lons)

    t_new = np.arange(t_sec[0], t_sec[-1], target_interval_seconds)
    if len(t_new) < 2:
        return lats, lons, timestamps

    lats_i = cs_lat(t_new)
    lons_i = cs_lon(t_new)

    timestamps_i = np.array([
        np.datetime64(int(t), "s").astype("datetime64[us]").astype(datetime)
        for t in t_new
    ])

    return lats_i, lons_i, timestamps_i


class GPSProcessor:
    """
    Full GPS processing pipeline:
    1. Remove duplicates
    2. Remove jumps
    3. Remove stationary points
    4. Interpolate to regular interval
    5. Compute segments, speeds, elevation
    """

    def __init__(
        self,
        max_jump_m: float = 500.0,
        duplicate_tolerance_m: float = 2.0,
        min_speed_ms: float = 0.5,
        interpolate_interval: Optional[float] = 5.0,
        smooth_window: int = 3,
    ):
        self.max_jump_m = max_jump_m
        self.duplicate_tolerance_m = duplicate_tolerance_m
        self.min_speed_ms = min_speed_ms
        self.interpolate_interval = interpolate_interval
        self.smooth_window = smooth_window

    def process(self, lats: list[float], lons: list[float],
                elevations: Optional[list[Optional[float]]] = None,
                timestamps: Optional[list[datetime]] = None) -> dict:
        if len(lats) < 2:
            raise ValueError("Need at least 2 GPS points")

        lat_arr = np.array(lats, dtype=np.float64)
        lon_arr = np.array(lons, dtype=np.float64)
        elev_arr = (
            np.array(elevations, dtype=np.float64)
            if elevations and any(e is not None for e in elevations)
            else None
        )

        timestamps = timestamps or [datetime.utcnow() for _ in range(len(lats))]
        ts_arr = np.array(timestamps, dtype="datetime64[us]")

        idx = self._clean_indices(lat_arr, lon_arr, ts_arr)

        lat_c = lat_arr[idx]
        lon_c = lon_arr[idx]
        elev_c = elev_arr[idx] if elev_arr is not None else None
        ts_c = ts_arr[idx]

        if self.interpolate_interval and len(lat_c) >= 2:
            lat_c, lon_c, ts_c = interpolate_gps(
                lat_c, lon_c, ts_c, self.interpolate_interval
            )
            if elev_c is not None:
                t_sec = ts_c.astype("datetime64[s]").astype(float)
                cs_elev = CubicSpline(
                    ts_arr.astype("datetime64[s]").astype(float)[idx], elev_arr[idx]
                )
                elev_c = cs_elev(t_sec)

        d = compute_segment_distances(lat_c, lon_c)
        dt = np.diff(ts_c).astype("datetime64[s]").astype(float)
        speeds = compute_speeds(d, dt)

        if self.smooth_window > 1:
            speeds = np.convolve(speeds, np.ones(self.smooth_window) / self.smooth_window, mode="same")

        total_dist = float(np.sum(d))

        elev_data = {}
        if elev_c is not None:
            gain, loss = compute_elevation_gain_loss(elev_c)
            elev_data = {
                "min_elevation": float(np.min(elev_c)),
                "max_elevation": float(np.max(elev_c)),
                "elevation_gain": gain,
                "elevation_loss": loss,
            }
        else:
            elev_data = {
                "min_elevation": None,
                "max_elevation": None,
                "elevation_gain": 0.0,
                "elevation_loss": 0.0,
            }

        duration = float((ts_c[-1] - ts_c[0]).astype("timedelta64[s]").astype(float))
        avg_speed = (total_dist / 1000) / (duration / 3600) if duration > 0 else 0.0
        max_speed = float(np.max(speeds)) if len(speeds) > 0 else 0.0

        return {
            "latitudes": lat_c,
            "longitudes": lon_c,
            "elevations": elev_c,
            "timestamps": ts_c,
            "distances_m": d,
            "speeds_kmh": speeds,
            "total_distance_m": total_dist,
            "duration_seconds": duration,
            "avg_speed_kmh": avg_speed,
            "max_speed_kmh": max_speed,
            "points_kept": len(lat_c),
            "points_removed": len(lats) - len(lat_c),
            **elev_data,
        }

    def _clean_indices(self, lats, lons, timestamps) -> np.ndarray:
        idx = np.arange(len(lats))
        idx = idx[remove_duplicates(lats, lons, self.duplicate_tolerance_m)]
        if len(idx) < 2:
            return idx
        idx = idx[remove_jumps(lats[idx], lons[idx], self.max_jump_m)]
        if len(idx) < 2:
            return idx
        idx = idx[remove_stationary_points(
            lats[idx], lons[idx], timestamps[idx], self.min_speed_ms
        )]
        return idx
